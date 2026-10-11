#!/usr/bin/python3
"""MA Home: Claude-Bruecke. Laeuft als Benutzer andrew (hat die Claude-Anmeldung) und nimmt
Auftraege des Portals (ma-web) ueber einen Unix-Socket an. Startet `claude -p` mit festen Rechten
und streamt die JSON-Zeilen zurueck. Kein TCP-Port, kein sudo (NoNewPrivileges)."""
import base64
import json
import os
import re
import select
import signal
import socketserver
import subprocess
import sys
import threading
import time
import uuid

SOCK = os.environ.get('MA_CLAUDE_SOCK', '/run/ma-claude/bridge.sock')
CLAUDE = '/home/andrew/.local/bin/claude'
DIRS = {
    'notizen': '/srv/ma-home/library/vault-notizen',
    'bibliothek': '/srv/ma-home/library',
    'server': '/home/andrew',
    'maserver': '/home/andrew/MA-Server',
}
READ_BASH = [f'Bash({c}:*)' for c in (
    'ls', 'cat', 'head', 'tail', 'df', 'du', 'uptime', 'free', 'ps', 'ss', 'systemctl status', 'systemctl list-timers',
    'systemctl is-active', 'journalctl', 'find', 'grep', 'wc', 'stat', 'date', 'lsblk')]
MODES = {
    'lesen': ('default', ['Read', 'Grep', 'Glob'] + READ_BASH),
    'plan': ('plan', ['Read', 'Grep', 'Glob'] + READ_BASH),      # Plan-Modus: Claude plant nur, nichts wird veraendert
    'notizen': ('acceptEdits', ['Read', 'Grep', 'Glob', 'Edit', 'Write'] + READ_BASH),
    # wie am PC: Dateien aendern und beliebige Befehle als andrew (ohne sudo). Gesperrtes steht in ~/.claude/settings.json (deny).
    # Wie am PC: alle Werkzeuge (auch Web und Verbindungen), ohne Rueckfragen. Grenzen: kein sudo (NoNewPrivileges),
    # deny-Regeln in ~/.claude/settings.json, Hook ma-guard.py sperrt Senden/Loeschen/Kaufen ueber Verbindungen.
    'voll': ('bypassPermissions', None),
    'voll_senden': ('bypassPermissions', None),
}
MODELS = ('haiku', 'sonnet', 'opus')
IMG_DIR = '/home/andrew/.ma-chat-bilder'
IMG_TYPES = {'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'image/gif': 'gif'}
HARD = re.compile(r'architektur|umbau|refactor|plane?n?\b|planung|strategie|sicherheitsl|code-?review|debugg?|fehlersuche', re.I)


try:                                   # gemeinsame Quelle fuer PC und Server: scripts/router/router_core.py
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import router_core
except ImportError:
    router_core = None


def pick_model(prompt, mode, has_images):
    """Auto-Modellwahl (Regel 11: Fable bleibt gesperrt). Opus nur fuer schwere Aufgaben, Haiku nur fuer kurze Fragen."""
    if router_core:
        return router_core.classify(prompt, mode, has_images)[0]
    if HARD.search(prompt) and len(prompt) > 200:
        return 'opus'
    if len(prompt) < 160 and not has_images and not str(mode).startswith('voll'):
        return 'haiku'
    return 'sonnet'


def save_images(images):
    """Speichert hochgeladene Bilder (data-URLs) privat und raeumt Dateien aelter als 7 Tage weg. Gibt Pfade zurueck."""
    os.makedirs(IMG_DIR, mode=0o700, exist_ok=True)
    for f in os.listdir(IMG_DIR):
        fp = os.path.join(IMG_DIR, f)
        try:
            if time.time() - os.path.getmtime(fp) > 7 * 86400:
                os.remove(fp)
        except OSError:
            pass
    paths = []
    for img in (images or [])[:3]:
        m = re.fullmatch(r'data:(image/[a-z+]+);base64,([A-Za-z0-9+/=]+)', img) if isinstance(img, str) else None
        if not m or m.group(1) not in IMG_TYPES:
            continue
        raw = base64.b64decode(m.group(2))
        if len(raw) > 5_000_000:
            continue
        fp = os.path.join(IMG_DIR, f'{int(time.time() * 1000)}-{len(paths)}.{IMG_TYPES[m.group(1)]}')
        with open(fp, 'wb') as fh:
            fh.write(raw)
        paths.append(fp)
    return paths
UP_DIR = '/home/andrew/.ma-chat-dateien'
UP_MAX = 8_000_000                          # je Datei
UP_UID = re.compile(r'[0-9a-f]{12}\Z')
UPLOADS = {}                                # (uid, name) -> naechster erwarteter Block
UP_LOCK = threading.Lock()


def safe_name(name):
    n = re.sub(r'[^A-Za-z0-9._ -]', '_', os.path.basename(str(name or '')))[:80].strip(' .')
    return n or 'datei'


def clean_uploads():
    try:
        for d in os.listdir(UP_DIR):
            dp = os.path.join(UP_DIR, d)
            if os.path.isdir(dp) and time.time() - os.path.getmtime(dp) > 7 * 86400:
                for f in os.listdir(dp):
                    os.remove(os.path.join(dp, f))
                os.rmdir(dp)
    except OSError:
        pass


def upload_chunk(req):
    """Nimmt eine Datei in Bloecken (Base64, je unter 90 KB) an. Gibt (ok, info) zurueck; beim letzten Block 'ref' = uid/name."""
    uid = str(req.get('uid') or '')
    if not UP_UID.fullmatch(uid):
        uid = uuid.uuid4().hex[:12]
    name, idx, total = safe_name(req.get('fname')), int(req.get('idx') or 0), int(req.get('total') or 1)
    if not 0 <= idx < total <= 120:
        return {'ok': False, 'error': 'Ungueltiger Block'}
    raw = base64.b64decode(str(req.get('data') or ''), validate=True)
    d = os.path.join(UP_DIR, uid)
    os.makedirs(d, mode=0o700, exist_ok=True)
    os.chmod(UP_DIR, 0o700)
    part = os.path.join(d, name + '.part')
    key = (uid, name)
    with UP_LOCK:
        if idx == 0:
            clean_uploads()
            UPLOADS[key] = 0
            open(part, 'wb').close()
        if UPLOADS.get(key) != idx:
            return {'ok': False, 'error': 'Block ausser der Reihe'}
        if os.path.getsize(part) + len(raw) > UP_MAX:
            os.remove(part)
            UPLOADS.pop(key, None)
            return {'ok': False, 'error': 'Datei zu gross (hoechstens 8 MB)'}
        with open(part, 'ab') as fh:
            fh.write(raw)
        UPLOADS[key] = idx + 1
        if idx + 1 == total:
            os.replace(part, os.path.join(d, name))
            UPLOADS.pop(key, None)
            return {'ok': True, 'done': True, 'uid': uid, 'ref': uid + '/' + name}
    return {'ok': True, 'done': False, 'uid': uid}


def upload_paths(refs):
    """Wandelt 'uid/name'-Verweise in vorhandene Dateipfade um (nur aus dem Upload-Ordner)."""
    out = []
    for ref in (refs or [])[:5]:
        uid, _, name = str(ref).partition('/')
        if UP_UID.fullmatch(uid) and name == safe_name(name):
            fp = os.path.join(UP_DIR, uid, name)
            if os.path.isfile(fp):
                out.append(fp)
    return out


SESSION = re.compile(r'[0-9a-f-]{36}\Z')
LIMIT = threading.BoundedSemaphore(2)
TIMEOUT = 900

JOBS = {}                                  # id -> {proc, start, prompt, model, mode}
JOBS_LOCK = threading.Lock()
PROJ = '/home/andrew/.claude/projects'
META = '/home/andrew/.ma-chat-names.json'  # eigene Sitzungsnamen (0600)
RESUMABLE = {cwd.replace('/', '-'): key for key, cwd in DIRS.items()}   # Ordnername unter projects -> Portal-Ordner


def kill_group(proc):
    """Beendet Claude samt Unterprozessen (eigene Prozessgruppe)."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        threading.Timer(3, lambda: proc.poll() is None and os.killpg(proc.pid, signal.SIGKILL)).start()
    except (ProcessLookupError, PermissionError):
        pass


def load_meta():
    try:
        return json.load(open(META, encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ' '.join(b.get('text', '') for b in content if isinstance(b, dict) and b.get('type') == 'text')
    return ''


def first_user(path):
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            for _ in range(400):
                line = fh.readline()
                if not line:
                    break
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get('type') == 'user':
                    t = ' '.join(text_of((d.get('message') or {}).get('content')).split())
                    if t and not t.startswith('<'):
                        return t[:90]
    except OSError:
        pass
    return ''


def find_session(sid):
    if not SESSION.fullmatch(sid or ''):
        return None
    try:
        for d in os.listdir(PROJ):
            p = os.path.join(PROJ, d, sid + '.jsonl')
            if os.path.isfile(p):
                return p, d
    except OSError:
        pass
    return None


def list_sessions(q):
    q = (q or '').strip().lower()[:100]
    meta, out, t0 = load_meta(), [], time.time()
    try:
        folders = os.listdir(PROJ)
    except OSError:
        return out
    for d in folders:
        dp = os.path.join(PROJ, d)
        if not os.path.isdir(dp):
            continue
        for f in os.listdir(dp):
            if not f.endswith('.jsonl') or not SESSION.fullmatch(f[:-6]):
                continue
            p, sid = os.path.join(dp, f), f[:-6]
            try:
                st = os.stat(p)
            except OSError:
                continue
            name = meta.get(sid) or ''
            title = name or first_user(p) or '(ohne Text)'
            if q and q not in title.lower():
                if st.st_size > 8_000_000 or time.time() - t0 > 6:
                    continue
                try:
                    if q not in open(p, encoding='utf-8', errors='replace').read().lower():
                        continue
                except OSError:
                    continue
            where = d.replace('-C-Users-andre-Documents-', 'PC ').replace('C--Users-andre-Documents-', 'PC ').strip('-')[:40]
            out.append({'id': sid, 'title': title, 'named': bool(name), 'time': int(st.st_mtime), 'size': st.st_size,
                        'where': where, 'dir': RESUMABLE.get(d)})
    out.sort(key=lambda x: x['time'], reverse=True)
    return out[:60]


def show_session(sid):
    found = find_session(sid)
    if not found:
        return None
    path, folder = found
    msgs = []
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            kind = d.get('type')
            if kind not in ('user', 'assistant'):
                continue
            t = text_of((d.get('message') or {}).get('content')).strip()
            if not t or t.startswith('<'):
                continue
            msgs.append({'r': 'u' if kind == 'user' else 'a', 't': t[:4000]})
    return {'msgs': msgs[-120:], 'dir': RESUMABLE.get(folder), 'folder': folder}



class Handler(socketserver.StreamRequestHandler):
    def reply(self, obj):
        self.wfile.write(json.dumps(obj).encode() + b'\n')
        self.wfile.flush()

    def op(self, req):
        """Verwaltungsbefehle (Portal-Route /api/claude/op): jobs, cancel, sessions, show, rename."""
        op = req.get('op')
        try:
            if op == 'jobs':
                with JOBS_LOCK:
                    jobs = [{'id': k, 'sec': int(time.time() - v['start']), 'prompt': v['prompt'], 'model': v['model'], 'mode': v['mode']} for k, v in JOBS.items()]
                return self.reply({'type': 'jobs', 'jobs': jobs})
            if op == 'cancel':
                with JOBS_LOCK:
                    job = JOBS.get(str(req.get('id')))
                if job:
                    kill_group(job['proc'])
                return self.reply({'type': 'cancel', 'ok': bool(job)})
            if op == 'suggest':
                if not router_core:
                    return self.reply({'type': 'suggest', 'ok': False})
                mode, folder, confirm = router_core.suggest_access(str(req.get('prompt') or '')[:2000])
                return self.reply({'type': 'suggest', 'ok': True, 'mode': mode, 'dir': folder, 'confirm': confirm})
            if op == 'upload':
                return self.reply({'type': 'upload', **upload_chunk(req)})
            if op == 'sessions':
                return self.reply({'type': 'sessions', 'sessions': list_sessions(req.get('q'))})
            if op == 'show':
                res = show_session(str(req.get('id')))
                return self.reply({'type': 'show', 'ok': bool(res), **(res or {})})
            if op == 'rename':
                sid, name = str(req.get('id')), ' '.join(str(req.get('name') or '').split())[:80]
                if not SESSION.fullmatch(sid):
                    return self.reply({'type': 'rename', 'ok': False})
                meta = load_meta()
                if name:
                    meta[sid] = name
                else:
                    meta.pop(sid, None)
                fd = os.open(META, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                    json.dump(meta, fh, ensure_ascii=False)
                return self.reply({'type': 'rename', 'ok': True})
        except Exception as exc:
            return self.reply({'type': 'bridge_error', 'error': type(exc).__name__})
        return self.reply({'type': 'bridge_error', 'error': 'Unbekannter Befehl'})

    def handle(self):
        try:
            req = json.loads(self.rfile.readline(131072))
            if req.get('op'):
                return self.op(req)
            prompt = req.get('prompt')
            if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 20000:
                return self.reply({'type': 'bridge_error', 'error': 'Ungueltiger Text'})
            cwd = DIRS.get(req.get('dir') or 'notizen')
            mode = MODES.get(req.get('mode') or 'lesen')
            img_paths = save_images(req.get('images'))
            if img_paths:
                prompt += '\n\n[Angehaengte Bilder, bitte mit dem Read-Werkzeug ansehen: ' + ', '.join(img_paths) + ']'
            file_paths = upload_paths(req.get('files'))
            if file_paths:
                prompt += '\n\n[Hochgeladene Dateien, bitte mit dem Read-Werkzeug oder passenden Werkzeugen ansehen: ' + ', '.join(file_paths) + ']'
            model = req.get('model') if req.get('model') in MODELS else pick_model(prompt, req.get('mode'), bool(img_paths))
            if not cwd or not mode:
                return self.reply({'type': 'bridge_error', 'error': 'Ungueltige Auswahl'})
            args = [CLAUDE, '-p', '--output-format', 'stream-json', '--verbose', '--include-partial-messages', '--model', model,
                    '--permission-mode', mode[0], '--max-turns', '40' if str(req.get('mode', '')).startswith('voll') else '12']
            if mode[1]:
                args += ['--allowedTools', ','.join(mode[1])]
            if img_paths:
                args += ['--add-dir', IMG_DIR]
            if file_paths:
                args += ['--add-dir', UP_DIR]
            if mode[1]:
                args += ['--strict-mcp-config']   # Lesen/Notizen brauchen keine Verbindungen: spart die lange Werkzeugliste (Token)
            sid = req.get('session')
            if isinstance(sid, str) and SESSION.fullmatch(sid):
                args += ['--resume', sid]
        except Exception:
            return self.reply({'type': 'bridge_error', 'error': 'Ungueltige Anfrage'})
        if not LIMIT.acquire(blocking=False):
            return self.reply({'type': 'bridge_error', 'error': 'Es laufen schon zwei Auftraege. Bitte warten.'})
        proc = None
        jid = None
        try:
            env = dict(os.environ, HOME='/home/andrew', PATH='/home/andrew/.local/bin:/usr/local/bin:/usr/bin:/bin')
            env.pop('MA_ALLOW_SEND', None)
            if req.get('mode') == 'voll_senden':
                env['MA_ALLOW_SEND'] = '1'
            self.reply({'type': 'bridge_model', 'model': model})
            proc = subprocess.Popen(args, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            jid = uuid.uuid4().hex[:12]
            with JOBS_LOCK:
                JOBS[jid] = {'proc': proc, 'start': time.time(), 'prompt': ' '.join(prompt.split())[:60], 'model': model, 'mode': str(req.get('mode'))}
            self.reply({'type': 'bridge_job', 'id': jid})
            proc.stdin.write(prompt.encode())
            proc.stdin.close()
            timer = threading.Timer(TIMEOUT, kill_group, [proc])
            timer.start()
            fd = proc.stdout.fileno()
            while True:
                ready, _, _ = select.select([fd, self.rfile], [], [], 10)
                if self.rfile in ready and not self.rfile.peek(1):
                    break                                   # Client weg
                if fd in ready:
                    chunk = os.read(fd, 65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
                else:
                    self.reply({'type': 'ping'})
            timer.cancel()
            code = proc.wait(timeout=5)
            self.reply({'type': 'bridge_end', 'code': code, 'err': proc.stderr.read(800).decode('utf-8', 'replace')})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:
            try:
                self.reply({'type': 'bridge_error', 'error': type(exc).__name__})
            except Exception:
                pass
        finally:
            if proc and proc.poll() is None:
                kill_group(proc)
            with JOBS_LOCK:
                JOBS.pop(jid, None)
            LIMIT.release()


class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


if __name__ == '__main__':
    if os.path.exists(SOCK):
        os.unlink(SOCK)
    os.umask(0o117)                                        # Socket 660 (andrew:ma-web)
    srv = Server(SOCK, Handler)
    os.umask(0o022)                                        # nur das Socket war 660; Claude soll normale Rechte (Ordner mit x) anlegen
    print('Claude-Bruecke bereit', SOCK, flush=True)
    srv.serve_forever()
