#!/usr/bin/python3
"""Fuegt /api/term in /opt/ma-home/portal.py ein (idempotent, mit Sicherung und Pruefung). Als root ausfuehren."""
import py_compile
import shutil
import sys
import time

P = sys.argv[1] if len(sys.argv) > 1 else '/opt/ma-home/portal.py'
MARK = '# --- MA-TERM-BRIDGE ---'
src = open(P, encoding='utf-8').read()
if MARK in src:
    print('Schon eingebaut.')
    sys.exit(0)
backup = f'{P}.bak-{time.strftime("%Y%m%d-%H%M%S")}'
shutil.copy2(P, backup)
ROUTE = f'''
{MARK}
TERM_SOCK = '/run/ma-term/bridge.sock'


@app.post('/api/term')
def term_run():
    """Befehl auf dem Server ausfuehren (nur Admin). Streamt JSON-Zeilen der Terminal-Bruecke."""
    if not g.admin:
        abort(403)
    body = request.get_json() or {{}}
    req = {{'cmd': body.get('cmd'), 'dir': body.get('dir'), 'user': g.user}}

    def generate():
        import select as _select
        try:
            with socket.socket(socket.AF_UNIX) as sock:
                sock.settimeout(5)
                sock.connect(TERM_SOCK)
                sock.sendall(json.dumps(req).encode() + b'\\n')
                sock.settimeout(None)
                while True:
                    ready, _, _ = _select.select([sock], [], [], 20)
                    if not ready:
                        yield b'{{"type":"ping"}}\\n'
                        continue
                    block = sock.recv(65536)
                    if not block:
                        break
                    yield block
        except OSError:
            yield b'{{"type":"error","error":"Terminal-Bruecke nicht erreichbar"}}\\n'

    return Response(stream_with_context(generate()), mimetype='application/x-ndjson', headers={{'X-Accel-Buffering': 'no'}})
'''
cut = src.rfind("\nif __name__")
new = src[:cut] + ROUTE + src[cut:] if cut >= 0 else src + ROUTE
open(P, 'w', encoding='utf-8').write(new)
try:
    py_compile.compile(P, doraise=True)
except py_compile.PyCompileError as exc:
    shutil.copy2(backup, P)
    sys.exit(f'Fehler, Sicherung wiederhergestellt: {exc}')
print(f'Eingebaut. Sicherung: {backup}')
