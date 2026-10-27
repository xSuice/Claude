"""Gemeinsame Modell- und Rechte-Wahl fuer PC und Server (eine Quelle, keine festen Pfade, kein Dateizugriff).

Verwendet von: server/claude-bridge/ma-claude-bridge.py (Portal-Chat) und, auf Wunsch, einem Hook am PC.
Tests: scripts/router/test_router_core.py   Doku: Vault `30 Technik/MA-Server/Server-Claude Variante 2.md`

Regeln: manuelle Wahl von Philipp hat Vorrang (nur haiku/sonnet/opus), Fable bleibt gesperrt,
Haiku nur bei klar einfachen Fragen, Opus nur bei klar schwerem Denken, sonst Sonnet.
Senden/Loeschen ('voll_senden') wird nie automatisch gewaehlt."""
import re

MODELS = ('haiku', 'sonnet', 'opus')       # Fable ist absichtlich nicht enthalten
MODES_READ = ('lesen', 'notizen')


def _any(text, patterns):
    return any(re.search(p, text, re.I) for p in patterns)


def _norm(text):
    return re.sub(r'\s+', ' ', text.lower()).strip()


OPUS = [r'\bzero[- ]trust\b', r'\bsicherheitsarchitektur\b', r'\bsecurity architecture\b', r'\bthreat model', r'\bbedrohungsmodell',
        r'\brace condition\b', r'\bdeadlock\b', r'\bschwer reproduzierbar', r'\bhard[- ]to[- ]reproduce',
        r'\bkomplex(?:e|es|en|er)? netzwerkproblem', r'\bcomplex network', r'\barchitektur.*sicherheit', r'\bsecurity.*architecture',
        r'\bschwerwiegend(?:e|en|er)? sicherheits', r'\bdeep architectural', r'\bgrundlegend(?:e|en|er)? architektur']
ARCH = [r'\barchitektur', r'\barchitecture', r'\bsystem design\b', r'\bdesign.*system']
SECURITY = [r'\bsicherheit', r'\bsicher(?:e|en|er|es)?\b', r'\bsecurity', r'\bauthentication', r'\bauthorization', r'\bzero trust']
COMPLEX = [r'\bkomplex', r'\bcomplex', r'\bumfangreich', r'\bdetailliert analys', r'\btiefgehend', r'\bdeep analysis']
PLANNING = [r'\bumbau', r'\bstrategie', r'\bplanung\b', r'\bpl[aä]ne? (?:mir|uns|einen|eine|das|die)\b']
WRITE = [r'\berstell(?:e|en)\b', r'\bschreib(?:e|en)\b', r'\bimplementier', r'\bänder(?:e|n)\b', r'\bmodifizier', r'\breparier', r'\bbeheb',
         r'\bfix(?:e|en)?\b', r'\brefactor', r'\brefaktor', r'\bfüge .* hinzu', r'\bentfern(?:e|en)\b', r'\bkonfigurier', r'\binstallier',
         r'\bmigrier', r'\boptimiere', r'\boptimize', r'\bcreate\b', r'\bwrite\b', r'\bimplement\b', r'\bmodify\b', r'\brepair\b']
DEBUG = [r'\bdebug', r'\bfehler beheben', r'\bbug\b', r'\bexception\b', r'\btraceback\b', r'\bwarum funktioniert', r'\bwarum geht',
         r'\bursache.*fehler']
SIMPLE = [r'^liste (?:mir )?(?:die )?dateien', r'^zeige (?:mir )?(?:die )?dateien', r'^welche dateien', r'^suche (?:nach )?',
          r'^finde (?:die |den |das )?.*(?:datei|config|konfiguration)', r'^was steht in .+', r'^lies .+(?:datei|readme)',
          r'^zeige .*status', r'^status (?:von|der|aller)', r'^docker ps', r'^git status', r'^git branch',
          r'^zeige .*docker-container', r'^liste .*docker-container']
NOT_HAIKU = [r'\berstell', r'\bschreib', r'\bänder', r'\bimplement', r'\brepar', r'\bbeheb', r'\bdebug', r'\barchitektur',
             r'\barchitecture', r'\bsicherheit', r'\bsecurity', r'\bkomplex', r'\bcomplex', r'\brefactor', r'\boptimi', r'\bmigrier']


# Council-Auftraege ("AI-Council:") laufen bewusst auf Sonnet, nicht auf Opus (siehe classify).
def classify(prompt, mode=None, has_images=False):
    """Gibt (modell, grund) zurueck. Rein regelbasiert, kein Modellaufruf."""
    p = _norm(prompt)
    if _any(p, OPUS):
        return 'opus', 'high_reasoning'
    if _any(p, ARCH) and _any(p, SECURITY):
        return 'opus', 'security_architecture'
    if _any(p, ARCH) and _any(p, COMPLEX):
        return 'opus', 'complex_architecture'
    if prompt.startswith('AI-Council:'):
        return 'sonnet', 'council'
    if _any(p, PLANNING) and len(p) > 200:
        return 'opus', 'planning'
    if _any(p, WRITE):
        return 'sonnet', 'write_or_modify'
    if _any(p, DEBUG):
        return 'sonnet', 'debugging'
    safe = not _any(p, NOT_HAIKU) and not has_images and len(p) <= 300
    if safe and mode in (*MODES_READ, None) and re.fullmatch(r'antworte nur mit (?:ok|ja|nein|bereit)[.!]?', p):
        return 'haiku', 'exact_ack_read_only'
    if safe and _any(p, SIMPLE):
        return 'haiku', 'clearly_simple_read_only'
    if safe and len(p) < 160 and (mode in MODES_READ or mode is None) and p.endswith('?'):
        return 'haiku', 'short_question'
    return 'sonnet', 'default'


def effort_for(model, reason):
    """Vorschlag fuer den Aufwand: niedrig bei Einfachem, hoch bei schwerem Denken."""
    if model == 'haiku':
        return 'low'
    if model == 'opus':
        return 'high'
    return 'high' if reason == 'debugging' else 'medium'


def choose(prompt, manual=None, mode=None, has_images=False):
    """Manuelle Wahl hat Vorrang (nur erlaubte Modelle). Gibt (modell, aufwand, grund) zurueck."""
    if manual in MODELS:
        return manual, effort_for(manual, 'manual'), 'manual'
    model, reason = classify(prompt, mode, has_images)
    return model, effort_for(model, reason), reason


# ---- Rechte und Ordner (Auto) -------------------------------------------------------------
_SERVER_WORDS = [r'\bserver\b', r'\bdocker\b', r'\bsystemd\b', r'\bdienst', r'\bcaddy\b', r'\bnetzwerk', r'\bpfad\b', r'\bprozess']
_MASERVER_WORDS = [r'\bskript', r'\bscript', r'\bportal\b', r'\bbrücke\b', r'\bbruecke\b', r'\brepo\b', r'\bcode\b', r'\bapp\b',
                   r'\breiter\b', r'\btab\b', r'\boberfläche\b', r'\boberflaeche\b', r'\bterminal\b', r'\bplayer\b', r'\bmusik\b', r'\bstatusbericht',
                   r'\bchangelog\b', r'\bbacklog\b', r'\btests?\b', r'\bapi\b', r'\bversion\b', r'\bautomatisier', r'\babgleich', r'\bkonnektor',
                   r'\bmcp\b', r'\bgithub\b', r'\bcron\b', r'\bfunktion\b', r'\bfeature\b', r'\bapp\.js\b', r'\.py\b', r'\.sh\b']
# Umsetzen am Projekt (zusaetzlich zu WRITE): wer so etwas schreibt, will dass Claude Dateien aendert und testet
_BUILD_WORDS = [r'\bbau(?:e|en)?\b', r'\bergänz', r'\berweiter', r'\bumsetz', r'\bsetze .* um\b', r'\baktualisier', r'\bverbesser', r'\bkorrigier',
                r'\bentwickl', r'\bprogrammier', r'\bmach(?:e)? (?:das|es|alles|weiter)\b', r'\bweiter\b', r'\btest(?:e|en)\b', r'\bpatch',
                r'\beinspiel', r'\bhinzufüg', r'\bregulier', r'\bautomatisch']
_LIB_WORDS = [r'\bdatei(?:en)?\b', r'\bbibliothek\b', r'\bpdf\b', r'\bpowerpoint\b', r'\bpptx\b', r'\bdocx\b', r'\bexcel\b', r'\bxlsx\b']
_NOTE_WRITE = [r'\bals notiz\b', r'\bnotier', r'\bübergabe', r'\buebergabe', r'\bspeichere\b', r'\bergänze\b', r'\bschreib.* (?:in|nach) ']
_CMD_WORDS = WRITE + [r'\bstarte\b', r'\bneu starten\b', r'\binstalliere\b', r'\bführe .* aus\b', r'\bausführen\b', r'\blösch']


def suggest_access(prompt):
    """Kleinste Rechte, die zum Auftrag passen. Gibt (modus, ordner, braucht_bestaetigung) zurueck.
    'voll_senden' wird NIE vorgeschlagen. 'voll' braucht immer die Bestaetigung im Portal."""
    p = _norm(prompt)
    if _any(p, _MASERVER_WORDS):
        folder = 'maserver'
    elif _any(p, _SERVER_WORDS):
        folder = 'server'
    elif _any(p, _LIB_WORDS):
        folder = 'bibliothek'
    else:
        folder = 'notizen'
    if (_any(p, _CMD_WORDS) or (folder == 'maserver' and _any(p, _BUILD_WORDS))) and folder != 'notizen':
        return 'voll', folder, True
    if _any(p, _NOTE_WRITE) and folder == 'notizen':
        return 'notizen', folder, False
    return 'lesen', folder, False


# ---- JARVIS (Cognitive Brain V11.1/V16): Ziel eines Arbeitsschritts ----------------------------
# Vertrag: docs/jarvis/v11.1/ROUTER-INTERFACE.md. Eingabe sind nur Metadaten (nie Inhalte); die
# Datenklasse hat JARVIS schon bestimmt, der Router darf sie nicht herabstufen. Externe Helfer
# nur fuer Klasse A (oeffentlich) und nur fuer lange, einfache, unkritische Texte (Regeln 8/12).
HELPER_TASKS = ('text_draft', 'translate', 'rewrite', 'summarize_public', 'prompt_improve')
HELPER_ORDER = ('gemini', 'openrouter')


def route_task(meta):
    """Gibt {'target': 'local'|'helper:<anbieter>'|'claude:<modell>'|'human', 'reason': ...} zurueck."""
    meta = meta if isinstance(meta, dict) else {}
    risk, dc = meta.get('risk'), meta.get('data_class')
    try:
        size = int(meta.get('size_chars') or 0)
    except (TypeError, ValueError):
        size = 0
    if risk == 'privileged' or risk not in ('read', 'reversible'):
        return {'target': 'human', 'reason': 'privileged_or_unknown_risk'}
    if meta.get('has_procedure') is True:
        return {'target': 'local', 'reason': 'confirmed_procedure'}
    if dc == 'public' and meta.get('task_type') in HELPER_TASKS and size >= 1500:
        return {'target': 'helper:' + HELPER_ORDER[0], 'reason': 'rule12_long_simple_public_text'}
    model = meta.get('model') if meta.get('model') in MODELS else 'sonnet'
    return {'target': 'claude:' + model, 'reason': 'default' if dc in ('public', 'internal') else 'private_data_stays_with_claude'}


if __name__ == '__main__':  # Aufruf als router.cmd: python3 router_core.py --route  (stdin: JSON, stdout: JSON)
    import json
    import sys
    if sys.argv[1:] == ['--route']:
        try:
            req = json.loads(sys.stdin.read(65536) or '{}')
        except ValueError:
            req = {}
        print(json.dumps(route_task(req)))
    else:
        print('Aufruf: router_core.py --route  (JSON auf stdin)', file=sys.stderr)
        raise SystemExit(2)
