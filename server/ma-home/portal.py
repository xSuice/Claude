#!/usr/bin/python3
"""MA Home: authenticated UI/API. Runs as ma-web, without Docker access."""
import datetime as dt
import errno
import hmac
import io
import json
import mimetypes
import os
from pathlib import Path
import re
import socket
import sqlite3
import stat
import time
import uuid
from decimal import Decimal, InvalidOperation

from flask import Flask, Response, abort, g, jsonify, request, send_file, send_from_directory, stream_with_context

ROOT = Path(os.environ.get('MA_ROOT', '/srv/ma-home'))
CONFIG = Path(os.environ.get('MA_CONFIG', '/etc/ma-home/portal.json'))
AGENT = os.environ.get('MA_AGENT', '/run/ma-home/agent.sock')
STATIC = Path(__file__).parent / 'web'
app = Flask(__name__, static_folder=None)
import sys; sys.path.insert(0, "/opt/jarvis/council")
from jarvis_portal_bridge import jarvis_bp
from chat_bus_backend import chat_bus_bp
app.register_blueprint(chat_bus_bp)
app.register_blueprint(jarvis_bp)
from jarvis_telemetry import telemetry_bp  # TELEMETRY-BP (read-only, admin)
app.register_blueprint(telemetry_bp)
from jarvis_health import health_bp  # HEALTH-BP: Dienstestatus aus Uptime Kuma
app.register_blueprint(health_bp)
from jarvis_voice import voice_bp  # VOICE-BP (admin, proxy to local PC voice service)
app.register_blueprint(voice_bp)
from chat_bus_mention_poller import start_mention_poller
start_mention_poller()
app.config['MAX_CONTENT_LENGTH'] = 128 * 1024
KINDS = {'tasks', 'notes', 'money', 'training'}
USERNAME = re.compile(r'[a-z][a-z0-9_-]{0,30}\Z')


def config():
    return json.loads(CONFIG.read_text())


def db():
    if 'db' not in g:
        g.db = sqlite3.connect(ROOT / 'portal' / 'home.sqlite', timeout=5)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db


def init_db():
    (ROOT / 'portal').mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(ROOT / 'portal' / 'home.sqlite') as conn:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('CREATE TABLE IF NOT EXISTS items (id TEXT PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL, changed INTEGER NOT NULL)')
        conn.execute('CREATE INDEX IF NOT EXISTS owner_kind ON items(owner, kind, changed)')


@app.teardown_appcontext
def close_db(error=None):
    if 'db' in g:
        g.db.close()


@app.before_request
def authorize():
    if request.path == '/healthz':
        return
    cfg = config()
    if not hmac.compare_digest(request.headers.get('X-MA-Key', ''), cfg['proxy_key']):
        abort(401)
    g.user = request.headers.get('Remote-User', '')
    if not USERNAME.fullmatch(g.user) or g.user not in cfg['users']:
        abort(403)
    g.admin = bool(cfg['users'][g.user].get('admin'))
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        if request.headers.get('Origin') != cfg['origin'] or request.headers.get('X-MA-Request') != '1':
            abort(403, 'Ungueltiger Ursprung der Anfrage')
        if not request.is_json:
            abort(415)


@app.after_request
def headers(response):
    # VENDOR-CACHE: versionierte Sprach-Engine-Dateien (WASM 11 MB, Modelle) privat cachen, alles andere no-store
    if request.path.startswith('/staging/js/vendor/') and response.status_code == 200:
        response.headers['Cache-Control'] = 'private, max-age=2592000, immutable'
    else:
        response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    return response


@app.errorhandler(Exception)
def error(exc):
    code = getattr(exc, 'code', 500)
    if code == 500:
        app.logger.error('Anfrage fehlgeschlagen: %s', type(exc).__name__)
    import traceback; open('/tmp/bridge_err.log','a').write(traceback.format_exc()+'\n'); return jsonify(error=getattr(exc, 'description', 'Interner Fehler; ma-home status pruefen.')), code


def agent(action, **data):
    payload = json.dumps({'action': action, 'user': g.user, **data}).encode() + b'\n'
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(12)
        sock.connect(AGENT)
        sock.sendall(payload)
        chunks = b''
        while b'\n' not in chunks:
            block = sock.recv(65536)
            if not block:
                raise RuntimeError('Agent getrennt')
            chunks += block
            if len(chunks) > 2 * 1024 * 1024:
                raise RuntimeError('Agent-Antwort zu gross')
    result = json.loads(chunks.split(b'\n')[0])
    if 'error' in result:
        abort(result.get('status', 400), result['error'])
    return result


def user_fd(path='', directory=False):
    """Walk only real directories below the authenticated user's root."""
    if not isinstance(path, str) or len(path) > 2048 or '\x00' in path or '\\' in path:
        abort(400, 'Ungueltiger Pfad')
    parts = path.split('/') if path else []
    if any(p in ('', '.', '..') or p.startswith('.') for p in parts):
        abort(403, 'Dieser Pfad ist nicht freigegeben')
    fd = os.open(ROOT / 'files' / g.user, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for index, part in enumerate(parts):
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            if directory or index < len(parts) - 1:
                flags |= os.O_DIRECTORY
            new = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = new
        st = os.fstat(fd)
        if not (stat.S_ISDIR(st.st_mode) if directory else stat.S_ISREG(st.st_mode)):
            abort(403, 'Nur regulaere Dateien und Ordner sind erlaubt')
        return fd
    except OSError as error:
        os.close(fd)
        abort(404 if error.errno == errno.ENOENT else 403, 'Datei oder Ordner ist nicht zugaenglich')
    except Exception:
        os.close(fd)
        raise


@app.get('/healthz')
def health():
    return jsonify(ok=True)


@app.get('/')
def index():   # M4-Cutover 2026-10-27: neue Shell (base href=/staging/); klassisch unter /classic/
    return send_from_directory(STATIC / 'staging', 'index.html')


@app.get('/classic')
@app.get('/classic/')
def classic_index():
    return send_from_directory(STATIC, 'index.html')


@app.get('/assets/<name>')
def assets(name):
    if name not in ('app.js', 'style.css', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png'):
        abort(404)
    return send_from_directory(STATIC, name)


@app.get('/sw.js')   # --- MA-PWA ---
def service_worker():
    response = send_from_directory(STATIC, 'sw.js', mimetype='application/javascript')
    response.headers['Service-Worker-Allowed'] = '/'
    return response


# --- MA-HOME HQ Staging (M1, 2026-10-27): Designsystem-Neuaufbau ---
@app.get('/staging')
@app.get('/staging/')
def staging_index():
    return send_from_directory(STATIC / 'staging', 'index.html')


@app.get('/staging/<path:name>')
def staging_files(name):
    return send_from_directory(STATIC / 'staging', name)


@app.get('/api/me')
def me():
    cfg = config()
    return jsonify(user=g.user, admin=g.admin, domain=cfg['origin'], modules=cfg.get('modules', {}))


@app.get('/api/status')
def status():
    return jsonify(agent('status'))


@app.post('/api/service')
def service():
    if not g.admin:
        abort(403)
    body = request.get_json()
    return jsonify(agent('service', service=body.get('service'), verb=body.get('verb')))


def text(value, maximum=1000, required=False):
    if not isinstance(value, str) or len(value) > maximum or '\x00' in value:
        abort(400, 'Text fehlt oder ist zu lang')
    value = value.strip()
    if required and not value:
        abort(400, 'Bitte das Pflichtfeld ausfuellen')
    return value


def date(value, optional=False):
    if optional and not value:
        return ''
    try:
        return dt.date.fromisoformat(value).isoformat()
    except (ValueError, TypeError):
        abort(400, 'Ungueltiges Datum')


def number(value, low, high):
    try:
        x = Decimal(str(value))
        if not x.is_finite() or not low <= x <= high:
            raise ValueError()
        return x
    except (InvalidOperation, ValueError, TypeError):
        abort(400, 'Zahl liegt ausserhalb des erlaubten Bereichs')


def item_body(kind, data):
    if not isinstance(data, dict):
        abort(400)
    if kind == 'tasks':
        return dict(title=text(data.get('title'), 240, True), due=date(data.get('due'), True), done=data.get('done') is True)
    if kind == 'notes':
        return dict(title=text(data.get('title'), 240, True), content=text(data.get('content', ''), 20000))
    if kind == 'money':
        cents = int((number(data.get('amount'), -10000000, 10000000) * 100).quantize(Decimal('1')))
        return dict(title=text(data.get('title'), 240, True), date=date(data.get('date')), category=text(data.get('category', ''), 80), cents=cents)
    return dict(exercise=text(data.get('exercise'), 240, True), date=date(data.get('date')), sets=int(number(data.get('sets'), 1, 100)), reps=int(number(data.get('reps'), 1, 10000)), kg=str(number(data.get('kg', 0), 0, 2000)), note=text(data.get('note', ''), 2000))


@app.route('/api/items/<kind>', methods=['GET', 'POST'])
def items(kind):
    if kind not in KINDS:
        abort(404)
    if request.method == 'GET':
        rows = db().execute('SELECT id,body,changed FROM items WHERE owner=? AND kind=? ORDER BY changed DESC LIMIT 2000', (g.user, kind))
        return jsonify(items=[dict(id=r['id'], changed=r['changed'], **json.loads(r['body'])) for r in rows])
    payload = item_body(kind, request.get_json())
    ident = str(uuid.uuid4())
    db().execute('INSERT INTO items VALUES(?,?,?,?,?)', (ident, g.user, kind, json.dumps(payload), int(time.time())))
    db().commit()
    return jsonify(id=ident), 201


@app.route('/api/items/<kind>/<ident>', methods=['PUT', 'DELETE'])
def item(kind, ident):
    if kind not in KINDS:
        abort(404)
    row = db().execute('SELECT id FROM items WHERE id=? AND owner=? AND kind=?', (ident, g.user, kind)).fetchone()
    if row is None:
        abort(404)
    if request.method == 'DELETE':
        db().execute('DELETE FROM items WHERE id=? AND owner=?', (ident, g.user))
    else:
        body = item_body(kind, request.get_json())
        db().execute('UPDATE items SET body=?,changed=? WHERE id=? AND owner=?', (json.dumps(body), int(time.time()), ident, g.user))
    db().commit()
    return jsonify(ok=True)


@app.get('/api/export')
def export():
    rows = db().execute('SELECT kind,body FROM items WHERE owner=? ORDER BY changed', (g.user,))
    data = {kind: [] for kind in KINDS}
    for row in rows:
        data[row['kind']].append(json.loads(row['body']))
    return send_file(io.BytesIO(json.dumps(data, ensure_ascii=False, indent=2).encode()), mimetype='application/json', as_attachment=True, download_name='ma-home-export.json')


@app.get('/api/files')
def files():
    path = request.args.get('path', '')
    fd = user_fd(path, directory=True)
    try:
        entries = []
        with os.scandir(fd) as scan:
            for entry in scan:
                if entry.name.startswith('.') or entry.is_symlink():
                    continue
                st = entry.stat(follow_symlinks=False)
                if not (stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode)):
                    continue
                entries.append(dict(name=entry.name, directory=stat.S_ISDIR(st.st_mode), size=st.st_size))
                if len(entries) >= 5000:
                    break
        entries.sort(key=lambda e: (not e['directory'], e['name'].casefold()))
        return jsonify(path=path, entries=entries)
    finally:
        os.close(fd)


@app.get('/api/file')
def file_get():
    path = request.args.get('path', '')
    fd = user_fd(path)
    return send_file(os.fdopen(fd, 'rb'), mimetype='application/octet-stream', as_attachment=True, download_name=Path(path).name)


@app.post('/api/jobs')
def jobs():
    body = request.get_json()
    kind = body.get('kind')
    if kind not in ('preview', 'print', 'scan'):
        abort(400)
    key = body.get('key', '')
    if not isinstance(key, str) or not re.fullmatch('[a-f0-9-]{36}', key):
        abort(400, 'Auftragskennung fehlt')
    return jsonify(agent('job', kind=kind, path=body.get('path', ''), key=key)), 202


@app.get('/api/jobs/<ident>')
def job_status(ident):
    return jsonify(agent('job-status', id=ident))


@app.get('/api/jobs/<ident>/page')
def job_page(ident):
    if not re.fullmatch('[a-f0-9-]{36}', ident):
        abort(404)
    result = agent('job-status', id=ident)
    if result.get('state') != 'done' or not result.get('preview'):
        abort(404)
    page = request.args.get('n', '1')
    if not page.isdigit() or not 1 <= int(page) <= result.get('pages', 0):
        abort(404)
    return send_file(ROOT / 'previews' / g.user / ident / ('page-%d.jpg' % int(page)), mimetype='image/jpeg')


# --- MA-CLAUDE-BRIDGE ---
CLAUDE_SOCK = '/run/ma-claude/bridge.sock'


@app.post('/api/claude')
def claude_chat():
    """Chat mit Claude auf dem Server (nur Admin). Streamt JSON-Zeilen der Claude-Bruecke."""
    if not g.admin:
        abort(403)
    body = request.get_json()
    req = {k: body.get(k) for k in ('prompt', 'session', 'dir', 'mode', 'model', 'images', 'files', 'attach', 'from', 'ctx')}   # CHAT-ROUTE-CTX

    def generate():
        import select as _select
        try:
            with socket.socket(socket.AF_UNIX) as sock:
                sock.settimeout(5)
                sock.connect(CLAUDE_SOCK)
                sock.sendall(json.dumps(req).encode() + b'\n')
                sock.settimeout(None)
                while True:
                    ready, _, _ = _select.select([sock], [], [], 20)
                    if not ready:
                        yield b'{"type":"ping"}\n'
                        continue
                    block = sock.recv(65536)
                    if not block:
                        break
                    yield block
        except OSError:
            yield b'{"type":"bridge_error","error":"Claude-Bruecke nicht erreichbar"}\n'

    return Response(stream_with_context(generate()), mimetype='application/x-ndjson', headers={'X-Accel-Buffering': 'no'})
# --- MA-CLAUDE-OPS ---
@app.post('/api/claude/op')
def claude_op():
    """Verwaltung der Claude-Bruecke (nur Admin): jobs, cancel, sessions, show, rename, suggest, upload."""
    if not g.admin:
        abort(403)
    body = request.get_json() or {}
    op = body.get('op')
    if op not in ('jobs', 'cancel', 'sessions', 'show', 'rename', 'suggest', 'upload', 'search', 'sched_list', 'sched_set', 'sched_del', 'usage', 'lern_feedback', 'note', 'connectors'):
        abort(400)
    req = {'op': op, 'id': str(body.get('id') or '')[:40], 'q': str(body.get('q') or '')[:100], 'name': str(body.get('name') or '')[:80],
           'prompt': str(body.get('prompt') or '')[:2000], 'uid': str(body.get('uid') or '')[:12], 'fname': str(body.get('fname') or '')[:120],
           'idx': int(body.get('idx') or 0), 'total': int(body.get('total') or 1), 'data': str(body.get('data') or '')[:100000]}
    try:
        with socket.socket(socket.AF_UNIX) as sock:
            sock.settimeout(15)
            sock.connect(CLAUDE_SOCK)
            sock.sendall(json.dumps(req).encode() + b'\n')
            data = b''
            while not data.endswith(b'\n') and len(data) < 3_000_000:
                block = sock.recv(65536)
                if not block:
                    break
                data += block
    except OSError:
        return jsonify(type='bridge_error', error='Claude-Bruecke nicht erreichbar'), 502
    return Response(data.strip() or b'{}', mimetype='application/json')


# --- MA-JARVIS ---
@app.post('/api/jarvis')
def jarvis_api():
    """JARVIS V16 (nur Admin): submit, list, status, events, result, cancel, approve, usage, caps, learned, meta, kill, forget."""
    if not g.admin:
        abort(403)
    body = request.get_json(silent=True) or {}
    cmd = body.get('cmd')
    if cmd not in ('submit', 'list', 'status', 'events', 'result', 'cancel', 'approve', 'revise', 'usage', 'councils', 'router', 'activity', 'knowledge', 'audit', 'caps', 'learned', 'meta', 'kill', 'forget', 'remember', 'memories'):   # N4-PORTAL
        abort(400)
    try:
        since, limit = int(body.get('since') or 0), int(body.get('limit') or 20)
    except (TypeError, ValueError):
        abort(400)
    req = {'op': 'jarvis', 'cmd': cmd, 'user': g.user, 'job': str(body.get('job') or '')[:40], 'since': since, 'limit': limit,
           'request': str(body.get('request') or '')[:8000], 'step': str(body.get('step') or '')[:60], 'answer': str(body.get('answer') or '')[:2000],
           'client_id': str(body.get('client_id') or '')[:60], 'expected': body.get('expected') if isinstance(body.get('expected'), int) else None, 'state': str(body.get('state') or '')[:3], 'kind': str(body.get('kind') or '')[:10], 'ident': str(body.get('ident') or '')[:80]}
    try:
        with socket.socket(socket.AF_UNIX) as sock:
            sock.settimeout(45)
            sock.connect(CLAUDE_SOCK)
            sock.sendall(json.dumps(req).encode() + b'\n')
            data = b''
            while not data.endswith(b'\n') and len(data) < 3_000_000:
                block = sock.recv(65536)
                if not block:
                    break
                data += block
    except OSError:
        return jsonify(type='bridge_error', error='Claude-Bruecke nicht erreichbar'), 502
    return Response(data.strip() or b'{}', mimetype='application/json')


# --- MA-CLAUDE-BRIDGE ----ENDE


# --- MA-DEPLOY-SWITCH ---
DEPLOY_SWITCH = '/srv/ma-home/deploy-schalter/erlaubt'


def _deploy_switch_on():
    return os.path.isfile(DEPLOY_SWITCH) and not os.path.islink(DEPLOY_SWITCH)


@app.route('/api/deploy/switch', methods=['GET', 'POST'])
def deploy_switch():
    """Admin-Schalter: darf die Auto-Einspielung (ma-deploy) Anforderungen ausfuehren? GET liest, POST {"on": true|false} setzt."""
    if not g.admin:
        abort(403)
    if request.method == 'POST':
        on = bool((request.get_json(silent=True) or {}).get('on'))
        try:
            if on:
                with open(DEPLOY_SWITCH, 'a'):
                    pass
            elif os.path.lexists(DEPLOY_SWITCH):
                os.remove(DEPLOY_SWITCH)
        except OSError:
            return jsonify(ok=False, error='Schalter nicht beschreibbar (Ordner /srv/ma-home/deploy-schalter pruefen)'), 500
    return jsonify(ok=True, on=_deploy_switch_on())


# --- MA-DEPLOY-SWITCH-ENDE ---

# --- MA-SUDO-SWITCH ---
SUDO_SWITCH = '/srv/ma-home/deploy-schalter/sudo-erlaubt'


def _sudo_switch_on():
    return os.path.isfile(SUDO_SWITCH) and not os.path.islink(SUDO_SWITCH)


@app.route('/api/deploy/sudo-switch', methods=['GET', 'POST'])
def sudo_switch():
    """Admin-Schalter: darf ma-sudo Skripte von Claude als root ausfuehren? GET liest, POST {"on": true|false} setzt."""
    if not g.admin:
        abort(403)
    if request.method == 'POST':
        on = bool((request.get_json(silent=True) or {}).get('on'))
        try:
            if on:
                with open(SUDO_SWITCH, 'a'):
                    pass
            elif os.path.lexists(SUDO_SWITCH):
                os.remove(SUDO_SWITCH)
        except OSError:
            return jsonify(ok=False, error='Schalter nicht beschreibbar (Ordner /srv/ma-home/deploy-schalter pruefen)'), 500
    return jsonify(ok=True, on=_sudo_switch_on())


# --- MA-SUDO-SWITCH-ENDE ---



# --- MA-AUDIO ---
AUDIO_TYPES = {'.mp3': 'audio/mpeg', '.m4a': 'audio/mp4', '.aac': 'audio/aac', '.ogg': 'audio/ogg', '.oga': 'audio/ogg', '.opus': 'audio/ogg',
               '.flac': 'audio/flac', '.wav': 'audio/wav', '.webm': 'audio/webm'}


@app.get('/api/audio')
def audio_get():
    """Audiodatei zum Abspielen (inline, Range). Nur bekannte Audio-Endungen."""
    path = request.args.get('path', '')
    mime = AUDIO_TYPES.get(Path(path).suffix.lower())
    if not mime:
        abort(415, 'Kein Audioformat')
    fd = user_fd(path)
    try:
        size = os.fstat(fd).st_size
        start, end, status = 0, size - 1, 200
        m = re.fullmatch(r'bytes=(\d*)-(\d*)', request.headers.get('Range', '').strip())
        if m and (m.group(1) or m.group(2)) and size:
            if m.group(1):
                start = int(m.group(1))
                end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
            else:
                start = max(size - int(m.group(2)), 0)
            if start > end or start >= size:
                os.close(fd)
                return Response(status=416, headers={'Content-Range': 'bytes */%d' % size})
            status = 206
    except Exception:
        os.close(fd)
        raise

    def chunks():
        try:
            pos = start
            while pos <= end:
                block = os.pread(fd, min(262144, end - pos + 1), pos)
                if not block:
                    break
                pos += len(block)
                yield block
        finally:
            os.close(fd)

    headers = {'Accept-Ranges': 'bytes', 'Content-Length': str(max(end - start + 1, 0)), 'Cache-Control': 'private, max-age=3600'}
    if status == 206:
        headers['Content-Range'] = 'bytes %d-%d/%d' % (start, end, size)
    return Response(stream_with_context(chunks()), status=status, mimetype=mime, headers=headers)

# --- MA-TERM-BRIDGE ---
TERM_SOCK = '/run/ma-term/bridge.sock'


@app.post('/api/term')
def term_run():
    """Befehl auf dem Server ausfuehren (nur Admin). Streamt JSON-Zeilen der Terminal-Bruecke."""
    if not g.admin:
        abort(403)
    body = request.get_json() or {}
    req = {'cmd': body.get('cmd'), 'dir': body.get('dir'), 'user': g.user}

    def generate():
        import select as _select
        try:
            with socket.socket(socket.AF_UNIX) as sock:
                sock.settimeout(5)
                sock.connect(TERM_SOCK)
                sock.sendall(json.dumps(req).encode() + b'\n')
                sock.settimeout(None)
                while True:
                    ready, _, _ = _select.select([sock], [], [], 20)
                    if not ready:
                        yield b'{"type":"ping"}\n'
                        continue
                    block = sock.recv(65536)
                    if not block:
                        break
                    yield block
        except OSError:
            yield b'{"type":"error","error":"Terminal-Bruecke nicht erreichbar"}\n'

    return Response(stream_with_context(generate()), mimetype='application/x-ndjson', headers={'X-Accel-Buffering': 'no'})

if __name__ == '__main__':
    from waitress import serve
    init_db()
    serve(app, host='127.0.0.1', port=18765, threads=4, connection_limit=50, channel_timeout=30, max_request_body_size=2*1024*1024, ident='')
