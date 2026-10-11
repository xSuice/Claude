#!/usr/bin/python3
"""MA Home: Claude-Bruecke. Laeuft als Benutzer andrew (hat die Claude-Anmeldung) und nimmt
Auftraege des Portals (ma-web) ueber einen Unix-Socket an. Startet `claude -p` mit festen Rechten
und streamt die JSON-Zeilen zurueck. Kein TCP-Port, kein sudo (NoNewPrivileges)."""
import base64
import json
import os
import re
import select
import socketserver
import subprocess
import sys
import threading
import time

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
HARD = re.compile(r'council|architektur|umbau|refactor|plane?n?\b|planung|strategie|sicherheitsl|code-?review|debugg?|fehlersuche', re.I)


try:                                   # gemeinsame Quelle fuer PC und Server: scripts/router/router_core.py
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import router_core
except ImportError:
    router_core = None


def pick_model(prompt, mode, has_images):
    """Auto-Modellwahl (Regel 11: Fable bleibt gesperrt). Opus nur fuer schwere Aufgaben, Haiku nur fuer kurze Fragen."""
    if router_core:
        return router_core.classify(prompt, mode, has_images)[0]
    if prompt.startswith('AI-Council:') or (HARD.search(prompt) and len(prompt) > 200):
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
SESSION = re.compile(r'[0-9a-f-]{36}\Z')
LIMIT = threading.BoundedSemaphore(2)
TIMEOUT = 900


class Handler(socketserver.StreamRequestHandler):
    def reply(self, obj):
        self.wfile.write(json.dumps(obj).encode() + b'\n')
        self.wfile.flush()

    def handle(self):
        try:
            req = json.loads(self.rfile.readline(131072))
            prompt = req.get('prompt')
            if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 20000:
                return self.reply({'type': 'bridge_error', 'error': 'Ungueltiger Text'})
            cwd = DIRS.get(req.get('dir') or 'notizen')
            mode = MODES.get(req.get('mode') or 'lesen')
            img_paths = save_images(req.get('images'))
            if img_paths:
                prompt += '\n\n[Angehaengte Bilder, bitte mit dem Read-Werkzeug ansehen: ' + ', '.join(img_paths) + ']'
            model = req.get('model') if req.get('model') in MODELS else pick_model(prompt, req.get('mode'), bool(img_paths))
            if not cwd or not mode:
                return self.reply({'type': 'bridge_error', 'error': 'Ungueltige Auswahl'})
            args = [CLAUDE, '-p', '--output-format', 'stream-json', '--verbose', '--include-partial-messages', '--model', model,
                    '--permission-mode', mode[0], '--max-turns', '40' if str(req.get('mode', '')).startswith('voll') else '12']
            if mode[1]:
                args += ['--allowedTools', ','.join(mode[1])]
            if img_paths:
                args += ['--add-dir', IMG_DIR]
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
        try:
            env = dict(os.environ, HOME='/home/andrew', PATH='/home/andrew/.local/bin:/usr/local/bin:/usr/bin:/bin')
            env.pop('MA_ALLOW_SEND', None)
            if req.get('mode') == 'voll_senden':
                env['MA_ALLOW_SEND'] = '1'
            self.reply({'type': 'bridge_model', 'model': model})
            proc = subprocess.Popen(args, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            proc.stdin.write(prompt.encode())
            proc.stdin.close()
            timer = threading.Timer(TIMEOUT, proc.kill)
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
                proc.kill()
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
