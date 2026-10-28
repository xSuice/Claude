"""/api/voice/* – proxy to the owner's local PC voice service (STT faster-whisper, TTS Piper) via SSH reverse tunnel.
Admin only (portal auth + CSRF checks of portal.py apply first). No audio or text is stored or logged here.
If the PC is off, the endpoints answer 503 and the portal falls back to browser speech."""
import base64, binascii, json, urllib.request, urllib.error
from flask import Blueprint, Response, abort, g, jsonify, request

voice_bp = Blueprint('jarvis_voice', __name__)
UPSTREAM = 'http://127.0.0.1:18790'
TOKEN_FILE = '/home/andrew/.config/ma-jarvis/voice-token'
MAX_AUDIO = 1200 * 1024  # 16 kHz PCM16 WAV from the browser engine ≈ 37 s (opus ≈ minutes)
# Only this route may exceed the portal-wide 128 KiB body limit (Flask >= 3.1 per-request limit); base64 + JSON overhead included.
STT_BODY_LIMIT = MAX_AUDIO * 4 // 3 + 4096
AUDIO = ('audio/webm', 'audio/ogg', 'audio/wav', 'audio/x-wav', 'audio/mp4', 'audio/mpeg', 'audio/aac')


def _token():
    try:
        with open(TOKEN_FILE, encoding='utf-8') as f:
            return f.read().strip()
    except OSError:
        return ''


def _call(path, body=None, ctype='application/json', timeout=60):
    req = urllib.request.Request(UPSTREAM + path, data=body, method='POST' if body is not None else 'GET')
    req.add_header('X-Voice-Token', _token())
    req.add_header('Content-Type', ctype)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get('Content-Type', ''), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('Content-Type', ''), e.read()
    except (urllib.error.URLError, OSError, TimeoutError):
        return 503, 'application/json', json.dumps({'error': 'Lokaler Sprachdienst nicht erreichbar (PC aus?)'}).encode()


def _admin():
    if not getattr(g, 'admin', False):
        abort(403)


@voice_bp.route('/api/voice/health', methods=['GET'])
def voice_health():
    _admin()
    code, _, body = _call('/health', timeout=5)
    if code != 200:
        return jsonify({'ok': False, 'error': 'Lokaler Sprachdienst nicht erreichbar'}), 200
    return Response(body, 200, mimetype='application/json')


@voice_bp.route('/api/voice/stt', methods=['POST'])
def voice_stt():
    """JSON body {mime, audio_b64} – portal.py only admits JSON POSTs (CSRF rule); route limit STT_BODY_LIMIT."""
    _admin()
    request.max_content_length = STT_BODY_LIMIT
    payload = request.get_json(silent=True) or {}
    ctype = str(payload.get('mime') or '').split(';', 1)[0].strip().lower()
    if ctype not in AUDIO:
        return jsonify({'error': 'Audioformat nicht unterstützt'}), 415
    try:
        data = base64.b64decode(str(payload.get('audio_b64') or ''), validate=True)
    except (binascii.Error, ValueError):
        return jsonify({'error': 'Audio nicht lesbar'}), 400
    if not data or len(data) > MAX_AUDIO:
        return jsonify({'error': 'Aufnahme leer oder zu groß'}), 413
    code, rtype, body = _call('/stt', data, ctype, timeout=60)
    return Response(body, code, mimetype=rtype.split(';')[0] or 'application/json')


@voice_bp.route('/api/voice/tts', methods=['POST'])
def voice_tts():
    _admin()
    payload = request.get_json(silent=True) or {}
    text = payload.get('text')
    if not isinstance(text, str) or not text.strip() or len(text) > 1500:
        return jsonify({'error': 'text ungültig'}), 400
    code, rtype, body = _call('/tts', json.dumps({'text': text}).encode(), timeout=60)
    resp = Response(body, code, mimetype=rtype.split(';')[0] or 'application/octet-stream')
    resp.headers['Cache-Control'] = 'no-store'
    return resp


# ---------- Gespräch mit Qwen lokal (PC, Ollama). 503 = nicht bereit -> Frontend nimmt Claude. ----------
@voice_bp.route('/api/voice/warm', methods=['POST'])
def voice_warm():
    _admin()
    code, rtype, body = _call('/warm', b'{}', timeout=8)
    return Response(body, code if code in (200, 503) else 503, mimetype='application/json')


@voice_bp.route('/api/voice/chat', methods=['POST'])
def voice_chat():
    """JSON {messages:[{role:user|assistant, content}]} (max. 12). Streamt NDJSON vom PC weiter; speichert und loggt nichts."""
    _admin()
    payload = request.get_json(silent=True) or {}
    msgs = payload.get('messages')
    if not isinstance(msgs, list) or not 1 <= len(msgs) <= 12:
        return jsonify({'error': 'messages ungültig'}), 400
    req = urllib.request.Request(UPSTREAM + '/chat', data=json.dumps({'messages': msgs}).encode(), method='POST')
    req.add_header('X-Voice-Token', _token())
    req.add_header('Content-Type', 'application/json')
    try:
        up = urllib.request.urlopen(req, timeout=25)
    except urllib.error.HTTPError as e:
        return Response(e.read(), e.code, mimetype='application/json')
    except (urllib.error.URLError, OSError, TimeoutError):
        return jsonify({'error': 'Lokaler Sprachdienst nicht erreichbar (PC aus?)'}), 503

    def gen():
        with up:
            for line in up:
                yield line
    resp = Response(gen(), 200, mimetype='application/x-ndjson')
    resp.headers['Cache-Control'] = 'no-store'
    resp.headers['X-Accel-Buffering'] = 'no'
    return resp
