"""MA-HOME local voice service (PC): speech-to-text and text-to-speech on 127.0.0.1 only.

Reached by the portal through an SSH reverse tunnel (ma-server 127.0.0.1:18790 -> PC 127.0.0.1:18790).
Every request needs the shared token (X-Voice-Token); audio and text stay on MA-HOME machines.
One job at a time, below-normal CPU priority (gaming keeps precedence). Logs carry no audio or text.
"""
import hmac, io, json, os, pathlib, sys, tempfile, threading, time, wave
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
        _models['stt'] = WhisperModel('base', device='cpu', compute_type='int8', cpu_threads=2, num_workers=1,
                                      download_root=str(ROOT / 'models/whisper'))
    return _models['stt']


def tts_voice():
    if 'tts' not in _models:
        from piper import PiperVoice
        _models['tts'] = PiperVoice.load(str(ROOT / 'models' / (VOICE + '.onnx')))
    return _models['tts']


def transcribe(data, suffix):
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data)
        path = f.name
    try:
        segments, info = stt_model().transcribe(path, language='de', beam_size=3, vad_filter=True,
                                                hotwords='Jarvis')
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
