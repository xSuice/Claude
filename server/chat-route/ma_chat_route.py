"""MA-HOME Chat-Weiche (29.10.): wer beantwortet eine Portal-Chat-Nachricht?

Andrews Vorgabe: automatisch und nicht auf Claude festgefahren - Fachfragen an die passende Hermes-Rolle (Nexum),
„Spezialisten“ und schwierige Entscheidungen an den Supervisor, Claude nur wo Werkzeuge/eigene Daten auf dem Server
nötig sind. Reihenfolge = Sicherheit vor Bequemlichkeit:
  1. feste Regeln (Bilder/Dateien, gewählter Modus/Modell, Befehle, eigene Daten, private Inhalte)  -> Claude
  2. ausdrückliche Wünsche („Spezialisten“, „Supervisor“, „frag Claude“)
  3. Fachgebiet per lokalem Qwen (PC-Sprachdienst /route, ~0,25 s) -> Rolle
  4. jeder Fehler, PC aus, unbekannte Antwort, Tageslimit -> Claude (bisheriges Verhalten)
Die Rollen antworten über den Mention-Receiver nur mit Lesewerkzeugen (kein Terminal, keine Dateien) - siehe ma-route-ask.py."""
import json
import os
import re
import threading
import time
import urllib.request

MODE = os.environ.get('MA_CHAT_ROUTE', 'auto')            # auto | off
VOICE = 'http://127.0.0.1:18790'
RECEIVER = 'http://127.0.0.1:8484'
VOICE_TOKEN_FILE = '/home/andrew/.config/ma-jarvis/voice-token'
STATE_FILE = '/home/andrew/.local/share/ma-claude/route-state.json'
LIMIT_SUPERVISOR = 15                                   # pro Tag (Supervisor nutzt das teure Modell)
LIMIT_ROLES = 200

ROLES = {'entwicklung': 'jarvis-cloud-dev', 'architektur': 'jarvis-architecture', 'sicherheit': 'jarvis-security',
         'betrieb': 'jarvis-server-fix', 'design': 'jarvis-design', 'planung': 'jarvis-planner', 'test': 'jarvis-qa',
         'abhaengigkeiten': 'jarvis-dependencies', 'recherche': 'jarvis-research', 'allgemein': 'jarvis-research',
         'entscheidung': 'kimi-supervisor'}
NAMES = {'entwicklung': 'Entwicklung', 'architektur': 'Architektur', 'sicherheit': 'Sicherheit', 'betrieb': 'Betrieb',
         'design': 'Design', 'planung': 'Planung', 'test': 'Tests', 'abhaengigkeiten': 'Abhängigkeiten',
         'recherche': 'Recherche', 'allgemein': 'Allgemein'}

W = lambda alts: re.compile(r'(?<![\w])(?:' + alts + r')(?![\w])', re.I)
# Befehle am Satzanfang (nach Füllwörtern) -> etwas TUN auf dem System
CMD = re.compile(r'^\s*(?:(?:hey|hi|jarvis|bitte|kannst du|kannste|könntest du|würdest du|mal|ma|jetzt|und|also|ok|okay)[\s,]+)*'
                 r'(?:mach|erstell|leg\w* an|lösch|loesch|sortier|prüf|pruef|check|schau|such|durchsuch|lies|les|schreib|schick|send|'
                 r'verschieb|kopier|install|starte?|stopp|beende|änder|aender|fix|reparier|öffne|oeffne|lad|benenn|räum|raeum|'
                 r'speicher|sicher\w* (?:das|die|den|mein)|exportier|importier|zeig|liste|fass\w*|übersetz|konvertier|'
                 r'aktualisier|update|backup|deploy|spiel|setz|dreh|gib mir (?:eine )?(?:liste|übersicht)|nutze den skill|'
                 r'erstelle nur einen plan|durchsuche meine)\w*', re.I)
MY_DATA = W(r'(?:mein|meine|meinen|meinem|meiner)\s+(?:notiz\w*|vault|dateien|datei|ordner|dokument\w*|unterlagen|mails?|e-mails?|'
            r'kalender|termine?|aufgaben|downloads?|bibliothek|fotos?|bilder|screenshots?|eingang|posteingang)|'
            r'im vault|in obsidian|im eingang|in der bibliothek')   # Fragen ÜBER den eigenen Server sind kein Datenzugriff; Aufträge fängt CMD
PRIVATE = W(r'(?:mein|meine|meinen|meinem|meiner)\s+(?:\w+\s+)?(?:passw\w*|kennw\w*|pin|tan|iban|konto\w*|kreditkarte\w*|gehalt|'
            r'lohn|steuer\w*|diagnose|krankheit\w*|therap\w*|medikament\w*|adresse|telefonnummer|geburtsdatum|ausweis\w*)|'
            r'(?:passw\w*|kennw\w*|pin)\s*(?:ist|lautet|:)|diagnose|arzt|[A-Z]{2}\d{2}(?:\s?\d{4}){4,7}')   # „ohne Passwort lauscht“ ist nicht privat
SUPERVISOR = W(r'supervisor|kimi|spezialist\w*|fachleute|experten|council|ai-council')
NO_ROUTE = re.compile(r'^\s*(?:frag (?:mal )?claude|claude[,:]|ohne router|ohne weiterleitung)', re.I)
SECRETISH = re.compile(r'\b(?:sk-|ghp_|gho_|xox[bap]-|AKIA)[A-Za-z0-9_-]{8,}|-----BEGIN [A-Z ]*PRIVATE KEY')


class State:
    """Tageszähler je Ziel (für Limits und das Command Center)."""

    def __init__(self, path=STATE_FILE):
        self.path, self.lock = path, threading.Lock()

    def _load(self):
        try:
            with open(self.path, encoding='utf-8') as f:
                d = json.load(f)
        except (OSError, ValueError):
            d = {}
        if d.get('day') != time.strftime('%Y-%m-%d'):
            d = {'day': time.strftime('%Y-%m-%d'), 'counts': {}}
        return d

    def used(self, target):
        with self.lock:
            return self._load()['counts'].get(target, 0)

    def count(self, target):
        with self.lock:
            d = self._load()
            d['counts'][target] = d['counts'].get(target, 0) + 1
            os.makedirs(os.path.dirname(str(self.path)) or '.', exist_ok=True)
            tmp = str(self.path) + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(d, f)
            os.replace(tmp, self.path)

    def report(self):
        with self.lock:
            return self._load()


def _token():
    try:
        with open(VOICE_TOKEN_FILE, encoding='utf-8') as f:
            return f.read().strip()
    except OSError:
        return ''


def fach_via_pc(text):
    req = urllib.request.Request(VOICE + '/route', data=json.dumps({'text': text[:1500]}).encode(), method='POST',
                                 headers={'X-Voice-Token': _token(), 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=4) as r:
        return json.load(r).get('fach')


def receiver_alive():
    try:
        with urllib.request.urlopen(RECEIVER + '/healthz', timeout=1.5) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def _claude(why, fach=None):
    return {'target': 'claude', 'why': why, 'fach': fach}


def decide(prompt, req, has_images=False, has_files=False, fach_of=fach_via_pc, state=None, alive=receiver_alive):
    """-> {'target': 'claude' | '<hermes-profil>', 'why': str, 'fach': str|None}. Führt nichts aus."""
    state = state or State()
    p = str(prompt or '')
    head = p.strip()[:400]
    if MODE != 'auto':
        return _claude('Weiche aus')
    if has_images or has_files:
        return _claude('Bilder/Dateien brauchen Werkzeuge')
    if str(req.get('mode') or 'auto') not in ('auto', 'lesen'):
        return _claude('Modus %s gewählt' % req.get('mode'))
    if str(req.get('model') or 'auto') not in ('auto', ''):
        return _claude('Modell ausdrücklich gewählt')
    if NO_ROUTE.match(head):
        return _claude('ausdrücklich Claude')
    if head.startswith('/') or CMD.match(head) or MY_DATA.search(p):
        return _claude('Auftrag oder eigene Daten: braucht Werkzeuge auf dem Server')
    if PRIVATE.search(p) or SECRETISH.search(p):
        return _claude('privater Inhalt: nicht an Nexum')
    if not alive():
        return _claude('PC/Fachrollen nicht erreichbar')
    wants_sup = bool(SUPERVISOR.search(head)) or head.startswith('AI-Council:')
    fach = None
    if not wants_sup:
        try:
            fach = fach_of(p)
        except Exception:  # noqa: BLE001 - PC aus, Qwen kalt, Zeitlimit
            return _claude('Fachgebiet nicht bestimmbar (PC/Qwen)')
        if fach == 'ausfuehren':
            return _claude('Qwen: Auftrag', fach)
        if fach not in ROLES:
            return _claude('Fachgebiet unbekannt: %r' % (fach,))
    target = 'kimi-supervisor' if wants_sup else ROLES[fach]
    why = ('ausdrücklich Supervisor/Spezialisten' if wants_sup else 'Fachgebiet %s' % fach)
    if target == 'kimi-supervisor' and state.used(target) >= LIMIT_SUPERVISOR:
        target, why = 'jarvis-planner', why + '; Supervisor-Tageslimit erreicht'
    if target != 'kimi-supervisor' and state.used('rollen') >= LIMIT_ROLES:
        return _claude('Tageslimit Fachrollen erreicht', fach)
    return {'target': target, 'why': why, 'fach': fach or ('entscheidung' if wants_sup else None)}


def label(d):
    if d['target'] == 'kimi-supervisor':
        return 'kimi-supervisor · Supervisor'
    if d['target'] == 'claude':
        return 'claude'
    return '%s · Nexum (Fachrolle %s)' % (d['target'], NAMES.get(d.get('fach'), d.get('fach') or ''))


ASK = '/usr/local/lib/ma-route-ask.py'
LOG_FILE = '/home/andrew/.local/share/ma-claude/route-log.jsonl'


def log(d, n_chars, log_file=LOG_FILE):
    """Jede Entscheidung (auch Claude) - ohne Inhalt, nur Ziel/Grund/Länge. Grundlage für Auswertung und Command Center."""
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps({'ts': int(time.time()), 'target': d['target'], 'fach': d.get('fach'), 'why': d['why'], 'chars': n_chars},
                               ensure_ascii=False) + '\n')
    except OSError:
        pass


def wrap(args, prompt, req, has_images=False, has_files=False, decide_fn=None, state=None, log_file=LOG_FILE, python='/usr/bin/python3'):
    """Für die Brücke: -> (args, env_extra, anzeige|None, entscheidung). Bei Claude bleiben die Argumente unverändert."""
    state = state or State()
    try:
        d = (decide_fn or decide)(prompt, req, has_images=has_images, has_files=has_files, state=state)
    except Exception:  # noqa: BLE001 - die Weiche darf den Chat nie blockieren
        d = _claude('Weiche-Fehler')
    log(d, len(prompt or ''), log_file)
    if d['target'] == 'claude':
        return args, {}, None, d
    state.count(d['target'])
    if d['target'] != 'kimi-supervisor':
        state.count('rollen')
    env = {'MA_ROUTE_CLAUDE_ARGS': json.dumps(args), 'MA_ROUTE_CTX': ' '.join(str(req.get('ctx') or '').split())[:2000]}
    return [python, ASK, d['target'], label(d)], env, label(d), d
