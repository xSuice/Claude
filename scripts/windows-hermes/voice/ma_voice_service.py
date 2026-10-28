"""MA-HOME local voice service (PC): speech-to-text and text-to-speech on 127.0.0.1 only.

Reached by the portal through an SSH reverse tunnel (ma-server 127.0.0.1:18790 -> PC 127.0.0.1:18790).
Every request needs the shared token (X-Voice-Token); audio and text stay on MA-HOME machines.
One job at a time, below-normal CPU priority (gaming keeps precedence). Logs carry no audio or text.
"""
import hmac, io, json, os, pathlib, re, sys, tempfile, threading, time, wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parent
TOKEN_FILE = pathlib.Path(os.environ.get('MA_VOICE_TOKEN_FILE', ROOT / 'voice-token.txt'))
HOST, PORT = '127.0.0.1', int(os.environ.get('MA_VOICE_PORT', '18790'))
MAX_AUDIO = 6 * 1024 * 1024
MAX_TEXT = 1500
VOICE = os.environ.get('MA_VOICE_MODEL', 'de_DE-thorsten_emotional-medium')
SPEAKER = int(os.environ.get('MA_VOICE_SPEAKER', '0'))  # 0 = "amused" (the sample the owner chose)
AUDIO_TYPES = {'audio/webm': '.webm', 'audio/ogg': '.ogg', 'audio/wav': '.wav', 'audio/x-wav': '.wav',
               'audio/mp4': '.m4a', 'audio/mpeg': '.mp3', 'audio/aac': '.aac'}
_lock = threading.Semaphore(1)
_models = {}


def base_type(content_type):
    return (content_type or '').split(';', 1)[0].strip().lower()


def check_token(expected, given):
    return bool(expected) and bool(given) and hmac.compare_digest(expected.encode(), given.encode())


def clean_text(value):
    if not isinstance(value, str):
        raise ValueError('text muss ein String sein')
    text = ' '.join(value.split())
    if not text:
        raise ValueError('text ist leer')
    if len(text) > MAX_TEXT:
        raise ValueError('text zu lang')
    return text


def stt_model():
    if 'stt' not in _models:
        os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
        from faster_whisper import WhisperModel
        _models['stt'] = WhisperModel('base', device='cpu', compute_type='int8', cpu_threads=4, num_workers=1,   # VOICE-004: 4 Threads 0,74 s statt 1,09 s je Satz, gleiche Trefferquote (stt_latency.py)
                                      download_root=str(ROOT / 'models/whisper'))
    return _models['stt']


def tts_voice():
    if 'tts' not in _models:
        from piper import PiperVoice
        _models['tts'] = PiperVoice.load(str(ROOT / 'models' / (VOICE + '.onnx')))
    return _models['tts']


# Fachwort-Prompt (gemessen 28.10. mit 8 Piper-Saetzen: base 0,75 -> 0,88 Worttreffer, gleiche Zeit; small war schlechter und 3,5x langsamer)
# PRIO2 N3 (28.10.): + Projektbegriffe. 16 Saetze: alt 0,88->0,86, neu 0,74->0,86. Langer Prompt mit allen Begriffen war schlechter (verwaessert).
STT_PROMPT = ('Jarvis, Auftrag, Aufträge, Minecraft, Modding, Fabric, Forge, Serverlogs, Command Center, Router, Signal, Portal, Uptime Kuma, '
              'Nexum, Crimson Zone, SMP, Eternal Bonds, Qwen, Living HQ, Watchdog.')


def transcribe(data, suffix):
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data)
        path = f.name
    try:
        segments, info = stt_model().transcribe(path, language='de', beam_size=3, vad_filter=True,
                                                hotwords='Jarvis', initial_prompt=STT_PROMPT)
        return ' '.join(s.text.strip() for s in segments).strip(), round(info.duration, 2)
    finally:
        os.unlink(path)


def synthesize(text):
    from piper import SynthesisConfig
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        tts_voice().synthesize_wav(text, w, syn_config=SynthesisConfig(speaker_id=SPEAKER, length_scale=1.0))
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    server_version = 'ma-voice/1'

    def chat(self, body):
        """Streamt NDJSON {"t": "..."} … {"done": true}. 503 wenn Qwen kalt ist oder die GPU belegt ist (Portal nimmt dann Claude)."""
        try:
            msgs = clean_messages(json.loads(body.decode('utf-8')).get('messages'))
        except (ValueError, json.JSONDecodeError, AttributeError) as e:
            return self.reply(400, {'error': str(e)[:120]})
        if chat_state() != 'warm':
            return self.reply(503, {'error': 'Qwen nicht bereit', 'state': warm_up()})
        try:
            up = _ollama('/api/chat', {'model': CHAT_MODEL, 'messages': [{'role': 'system', 'content': CHAT_SYS}] + msgs, 'stream': True, 'think': False,
                                        'keep_alive': KEEP_ALIVE, 'options': {'num_ctx': 4096, 'temperature': 0.6, 'num_predict': 220}}, timeout=20)
        except (OSError, ValueError):
            return self.reply(503, {'error': 'Ollama nicht erreichbar'})
        self.send_response(200)
        self.send_header('Content-Type', 'application/x-ndjson')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Connection', 'close')
        self.end_headers()
        try:
            with up:
                for line in up:
                    try:
                        d = json.loads(line)
                    except ValueError:
                        continue
                    piece = (d.get('message') or {}).get('content') or ''
                    if piece:
                        self.wfile.write((json.dumps({'t': piece}, ensure_ascii=False) + '\n').encode()); self.wfile.flush()
                    if d.get('done'):
                        break
            self.wfile.write(b'{"done": true}\n')
        except (OSError, ValueError):
            pass

    def intent(self, body):
        """PRIO2 N1: {text, run|null} -> {intent, text, ms}. 503 kalt/GPU belegt, 502 unbrauchbare Modellantwort.
        In beiden Faellen nutzt das Portal seine Satzmuster (altes Verhalten). Fuehrt nie etwas aus."""
        try:
            req = json.loads(body.decode('utf-8'))
            text, run = clean_intent_input(req.get('text'), req.get('run'))
        except (ValueError, json.JSONDecodeError, AttributeError) as e:
            return self.reply(400, {'error': str(e)[:120]})
        if chat_state() != 'warm':
            return self.reply(503, {'error': 'Qwen nicht bereit', 'state': warm_up()})
        t0 = time.time()
        try:
            res = classify_intent(text, run)
        except (OSError, ValueError):
            return self.reply(503, {'error': 'Ollama nicht erreichbar'})
        if res is None:
            return self.reply(502, {'error': 'Absicht nicht erkannt'})
        res['ms'] = int((time.time() - t0) * 1000)
        return self.reply(200, res)

    def log_message(self, fmt, *args):  # no paths/bodies in logs
        sys.stderr.write('%s %s %s\n' % (time.strftime('%H:%M:%S'), self.command, args[1] if len(args) > 1 else ''))

    def reply(self, code, body, ctype='application/json'):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        expected = TOKEN_FILE.read_text(encoding='utf-8').strip() if TOKEN_FILE.exists() else ''
        return check_token(expected, self.headers.get('X-Voice-Token', ''))

    def do_GET(self):
        if self.path == '/chat/state':
            if not self.authorized():
                return self.reply(401, {'error': 'nicht autorisiert'})
            return self.reply(200, {'state': chat_state(), 'model': CHAT_MODEL})
        if self.path != '/health':
            return self.reply(404, {'error': 'unbekannt'})
        if not self.authorized():
            return self.reply(401, {'error': 'nicht autorisiert'})
        return self.reply(200, {'ok': True, 'voice': VOICE, 'speaker': SPEAKER, 'stt': 'faster-whisper base'})

    def do_POST(self):
        if not self.authorized():
            return self.reply(401, {'error': 'nicht autorisiert'})
        try:
            length = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            length = -1
        if length <= 0 or length > MAX_AUDIO:
            return self.reply(413, {'error': 'Größe ungültig'})
        body = self.rfile.read(length)
        if self.path == '/warm':
            return self.reply(200, {'state': warm_up(), 'model': CHAT_MODEL})
        if self.path == '/chat':
            return self.chat(body)
        if self.path == '/intent':
            return self.intent(body)
        if not _lock.acquire(timeout=20):
            return self.reply(503, {'error': 'Sprachdienst ist gerade belegt'})
        try:
            t0 = time.time()
            if self.path == '/stt':
                suffix = AUDIO_TYPES.get(base_type(self.headers.get('Content-Type')))
                if not suffix:
                    return self.reply(415, {'error': 'Audioformat nicht unterstützt'})
                text, duration = transcribe(body, suffix)
                return self.reply(200, {'text': text, 'audio_s': duration, 'elapsed_s': round(time.time() - t0, 2)})
            if self.path == '/tts':
                text = clean_text(json.loads(body.decode('utf-8')).get('text'))
                return self.reply(200, synthesize(text), 'audio/wav')
            return self.reply(404, {'error': 'unbekannt'})
        except (ValueError, json.JSONDecodeError) as e:
            return self.reply(400, {'error': str(e)[:120]})
        except Exception as e:  # never leak content; only the type
            return self.reply(500, {'error': 'Sprachdienst-Fehler: ' + type(e).__name__})
        finally:
            _lock.release()


# ---------- Gesprächs-LLM: Qwen lokal über Ollama (privat, kostenlos). Gaming hat Vorrang. ----------
import subprocess, urllib.request, urllib.error
OLLAMA = 'http://127.0.0.1:11434'
CHAT_MODEL = os.environ.get('MA_CHAT_MODEL', 'qwen3:8b')
KEEP_ALIVE = '15m'                  # danach gibt Ollama den Grafikspeicher wieder frei
GPU_BUSY_MIB = 1500                 # belegt schon etwas anderes (Spiel) so viel VRAM, wird Qwen nicht geladen
CHAT_SYS = ('Du bist JARVIS, der persönliche Assistent von Andrew im MA-HOME. Sprich natürliches, freundliches Deutsch wie in einem echten Gespräch: '
            'höchstens drei kurze Sätze, kein Markdown, keine Listen, keine Emojis, keine Links. Bleib bei Fakten ehrlich: wenn du unsicher bist, sag es. '
            'Du hast keinen Zugriff auf Dateien, Notizen oder Aufträge und behauptest nie, etwas nachgesehen oder erledigt zu haben.')
_warm = {'state': 'off', 'since': 0.0}
_warm_lock = threading.Lock()


def _ollama(path, body=None, timeout=5):
    req = urllib.request.Request(OLLAMA + path, data=None if body is None else json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    return urllib.request.urlopen(req, timeout=timeout)


def model_loaded():
    try:
        with _ollama('/api/ps', timeout=3) as r:
            return any(m.get('name') == CHAT_MODEL or m.get('model') == CHAT_MODEL for m in json.load(r).get('models', []))
    except (OSError, ValueError):
        return False


def gpu_used_mib():
    try:
        out = subprocess.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout
        return int(out.strip().splitlines()[0])
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


def chat_state():
    if model_loaded():
        _warm['state'] = 'warm'
    elif _warm['state'] == 'warm':
        _warm['state'] = 'off'
    return _warm['state']


def warm_up():
    """Laedt das Modell im Hintergrund (Kaltstart ~1 min). Nicht, wenn die GPU schon belegt ist (Spiel)."""
    if chat_state() == 'warm':
        return 'warm'
    used = gpu_used_mib()
    if used is not None and used > GPU_BUSY_MIB:
        _warm['state'] = 'busy'
        return 'busy'
    with _warm_lock:
        if _warm['state'] == 'loading' and time.time() - _warm['since'] < 180:
            return 'loading'
        _warm.update(state='loading', since=time.time())

    def run():
        try:
            with _ollama('/api/generate', {'model': CHAT_MODEL, 'prompt': '', 'keep_alive': KEEP_ALIVE}, timeout=240) as r:
                r.read()
            _warm['state'] = 'warm' if model_loaded() else 'off'
        except (OSError, ValueError):
            _warm['state'] = 'off'
    threading.Thread(target=run, daemon=True).start()
    return 'loading'


def clean_messages(msgs):
    if not isinstance(msgs, list) or not 1 <= len(msgs) <= 12:
        raise ValueError('messages ungültig')
    out = []
    for m in msgs:
        role, content = (m or {}).get('role'), (m or {}).get('content')
        if role not in ('user', 'assistant') or not isinstance(content, str) or not content.strip():
            raise ValueError('message ungültig')
        out.append({'role': role, 'content': content.strip()[:2000]})
    if out[-1]['role'] != 'user':
        raise ValueError('letzte Nachricht muss vom Nutzer sein')
    return out


# ---------- PRIO2 N1: Absichtserkennung (dasselbe geladene Modell -> kein Tausch im Grafikspeicher) ----------
INTENTS = ('submit', 'revise', 'cancel', 'progress', 'none')
INTENT_MAX_TEXT = 300
INTENT_SCHEMA = {'type': 'object', 'required': ['intent', 'text'],
                 'properties': {'intent': {'type': 'string', 'enum': list(INTENTS)}, 'text': {'type': 'string'}}}
INTENT_SYS = '''Du ordnest eine gesprochene deutsche Äußerung an den Heimassistenten JARVIS einer Absicht zu. JARVIS erledigt Aufträge (Jobs).
Die Nachricht beginnt mit [Kontext: ...]: entweder der gerade laufende Auftrag oder "kein laufender Auftrag". Danach folgt die Äußerung.
Antworte nur mit JSON {"intent": ..., "text": ...}.

intent:
- "submit": eine NEUE Arbeit für JARVIS mit eigenem Gegenstand – auch als höfliche Frage ("Kannst du mir … zusammenfassen?") oder Wunsch ("Ich brauche eine Liste …"). Ein laufender Auftrag ändert daran nichts: neue Tätigkeit mit neuem Gegenstand = submit. text = die Aufgabe, knapp.
- "revise": die Äußerung bezieht sich auf den LAUFENDEN Auftrag und ändert, ergänzt oder schränkt ihn ein. Typisch: "dabei", "auch noch", "lieber", "stattdessen", "doch nur", "nicht X sondern Y", "und dann …", Bezug mit "das/die/es" auf das laufende Ergebnis. text = die Änderung.
- "cancel": der laufende Auftrag soll aufhören oder verworfen werden. text = "".
- "progress": Frage nach Stand, Dauer, Ergebnis oder Problemen eines Auftrags. text = "".
- "none": Gespräch, Wissensfragen, Dank, Lob, Begrüßung, Fragen zu JARVIS selbst. text = "".
Faustregel: Kann JARVIS sofort mit Wissen antworten -> none. Soll JARVIS etwas an Dateien, Servern, Diensten oder Daten TUN -> submit (neu) oder revise (laufend).

Beispiele:
[Kontext: laufender Auftrag "Fotos vom Urlaub umbenennen"] Leg mir außerdem eine Liste der Server-Updates an -> {"intent":"submit","text":"Liste der Server-Updates anlegen"}
[Kontext: laufender Auftrag "Fotos vom Urlaub umbenennen"] Nimm dabei bitte das Datum in den Namen -> {"intent":"revise","text":"Datum in den Dateinamen aufnehmen"}
[Kontext: laufender Auftrag "Logs zusammenfassen"] Lieber nur die Fehler -> {"intent":"revise","text":"nur die Fehler"}
[Kontext: laufender Auftrag "Logs zusammenfassen"] Vergiss es, brauch ich nicht -> {"intent":"cancel","text":""}
[Kontext: kein laufender Auftrag] Prüf mal, ob alle Dienste laufen -> {"intent":"submit","text":"prüfen, ob alle Dienste laufen"}
[Kontext: laufender Auftrag "Backup erstellen"] Klappt das? -> {"intent":"progress","text":""}
[Kontext: kein laufender Auftrag] Was ist ein Backup? -> {"intent":"none","text":""}'''


_INTENT_RE = re.compile(r'"intent"\s*:\s*"([a-z]+)"')


def clean_intent_input(text, run):
    if not isinstance(text, str) or not text.strip() or len(text) > 500:
        raise ValueError('text ungültig')
    if run is not None and (not isinstance(run, str) or len(run) > 300):
        raise ValueError('run ungültig')
    return ' '.join(text.split()), (' '.join(run.split()) or None) if run else None


def classify_intent(text, run):
    """Liefert {'intent', 'text'} oder None bei unbrauchbarer Modellantwort (nie geraten)."""
    ctx = 'laufender Auftrag "%s"' % run if run else 'kein laufender Auftrag'
    body = {'model': CHAT_MODEL, 'stream': True, 'think': False, 'format': INTENT_SCHEMA, 'keep_alive': KEEP_ALIVE,
            'options': {'temperature': 0, 'num_predict': 80, 'num_ctx': 4096},   # = Chat-num_ctx, sonst laedt Ollama das Modell neu
            'messages': [{'role': 'system', 'content': INTENT_SYS}, {'role': 'user', 'content': '[Kontext: %s] %s' % (ctx, text)}]}
    # Streamen und abbrechen, sobald die Absicht feststeht: sie wird laut Schema VOR dem Text erzeugt (temperature 0),
    # das Ergebnis ist also identisch zum vollstaendigen Lauf, spart aber die Text-Token (~1,4 s -> ~0,9 s gemessen).
    raw = ''
    with _ollama('/api/chat', body, timeout=8) as r:
        for line in r:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            raw += (d.get('message') or {}).get('content') or ''
            m = _INTENT_RE.search(raw)
            if m or d.get('done'):
                break
    m = _INTENT_RE.search(raw)
    intent = m.group(1) if m else None
    if intent not in INTENTS:
        return None
    # Auftrags-/Aenderungstext = Andrews Wortlaut (normalisiert); die Engine plant daraus selbst.
    return {'intent': intent, 'text': text[:INTENT_MAX_TEXT] if intent in ('submit', 'revise') else ''}


def lower_priority():
    if os.name == 'nt':
        import ctypes
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00004000)


def main():
    if sys.stderr is None:  # pythonw has no console; keep a small status log (no audio/text content)
        sys.stderr = open(ROOT / 'ma_voice_service.log', 'a', encoding='utf-8', buffering=1)
    lower_priority()
    threading.Thread(target=lambda: (stt_model(), tts_voice()), daemon=True).start()  # prewarm: first reply fast
    ThreadingHTTPServer.daemon_threads = True
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    sys.stderr.write('ma-voice bereit auf %s:%d\n' % (HOST, PORT))
    srv.serve_forever()


if __name__ == '__main__':
    main()
