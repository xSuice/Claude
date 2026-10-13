#!/usr/bin/python3
"""MA Home: Terminal-Bruecke. Laeuft als Benutzer andrew (kein sudo, NoNewPrivileges) und nimmt Befehle des Portals (ma-web)
ueber einen Unix-Socket an. Fuehrt jeden Befehl mit `bash -c` aus (kein interaktives Terminal), streamt die Ausgabe als JSON-Zeilen.
Beendet den Prozess bei Zeitueberschreitung oder wenn der Client die Verbindung schliesst."""
import json
import os
import select
import signal
import socketserver
import subprocess
import threading
import time

SOCK = os.environ.get('MA_TERM_SOCK', '/run/ma-term/bridge.sock')
TIMEOUT = 120
DIRS = {'server': '/home/andrew', 'maserver': '/home/andrew/MA-Server', 'bibliothek': '/srv/ma-home/library', 'notizen': '/srv/ma-home/library/vault-notizen'}
LIMIT = threading.Semaphore(2)
_JARVIS = '/srv/ma-home/library/.jarvis'                              # unter /srv/ma-home, damit das Protokoll im Backup ist
LOG = os.environ.get('MA_TERM_LOG', os.path.join(_JARVIS, 'term.log') if os.path.isdir(_JARVIS) else '/home/andrew/.ma-term.log')   # Zeit, Benutzer, Ordner, Befehl (0600, bei 1 MB halbiert)


def audit(user, folder, cmd):
    try:
        if os.path.exists(LOG) and os.path.getsize(LOG) > 1_000_000:
            with open(LOG, 'rb') as fh:
                fh.seek(-500_000, os.SEEK_END)
                tail = fh.read().split(b'\n', 1)[-1]
            fd = os.open(LOG, os.O_WRONLY | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'wb') as fh:
                fh.write(tail)
        fd = os.open(LOG, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write('%s\t%s\t%s\t%s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), ''.join(c for c in str(user or '?')[:32] if c.isalnum() or c in '_-'),
                                            folder, ' '.join(cmd.split())[:2000]))
    except OSError:
        pass


def kill_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except OSError:
        pass


class Handler(socketserver.StreamRequestHandler):
    def reply(self, obj):
        self.wfile.write(json.dumps(obj).encode() + b'\n')
        self.wfile.flush()

    def handle(self):
        try:
            req = json.loads(self.rfile.readline(20000))
            cmd = req.get('cmd')
            cwd = DIRS.get(req.get('dir') or 'server')
            if not isinstance(cmd, str) or not cmd.strip() or len(cmd) > 8000 or not cwd:
                return self.reply({'type': 'error', 'error': 'Ungueltige Anfrage'})
        except Exception:
            return self.reply({'type': 'error', 'error': 'Ungueltige Anfrage'})
        if not LIMIT.acquire(blocking=False):
            return self.reply({'type': 'error', 'error': 'Es laufen schon zwei Befehle. Bitte warten.'})
        proc = None
        audit(req.get('user'), req.get('dir') or 'server', cmd)
        try:
            env = dict(os.environ, HOME='/home/andrew', PATH='/home/andrew/.local/bin:/usr/local/bin:/usr/bin:/bin', TERM='dumb', LANG='C.UTF-8')
            proc = subprocess.Popen(['/bin/bash', '-c', cmd], cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            timer = threading.Timer(TIMEOUT, kill_group, [proc])
            timer.start()
            fd = proc.stdout.fileno()
            sent = 0
            while True:
                ready, _, _ = select.select([fd, self.rfile], [], [], 10)
                if self.rfile in ready and not self.rfile.peek(1):
                    break                                    # Client weg
                if fd in ready:
                    chunk = os.read(fd, 65536)
                    if not chunk:
                        break
                    sent += len(chunk)
                    if sent > 2_000_000:
                        self.reply({'type': 'out', 't': '\n[Ausgabe auf 2 MB begrenzt, Befehl beendet]\n'})
                        kill_group(proc)
                        break
                    self.reply({'type': 'out', 't': chunk.decode('utf-8', 'replace')})
                elif not ready:
                    self.reply({'type': 'ping'})
            timer.cancel()
            code = proc.wait(timeout=5)
            self.reply({'type': 'end', 'code': code})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:
            try:
                self.reply({'type': 'error', 'error': type(exc).__name__})
            except Exception:
                pass
        finally:
            if proc and proc.poll() is None:
                kill_group(proc)
            LIMIT.release()


class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


if __name__ == '__main__':
    if os.path.exists(SOCK):
        os.unlink(SOCK)
    os.umask(0o117)                                          # Socket 660 (andrew:ma-web)
    srv = Server(SOCK, Handler)
    print('Terminal-Bruecke bereit', SOCK, flush=True)
    srv.serve_forever()
