#!/usr/bin/python3
"""Fuegt /api/claude in /opt/ma-home/portal.py ein (idempotent, mit Sicherung und Pruefung). Als root ausfuehren."""
import py_compile
import shutil
import sys
import time

P = sys.argv[1] if len(sys.argv) > 1 else '/opt/ma-home/portal.py'
MARK = '# --- MA-CLAUDE-BRIDGE ---'
src = open(P, encoding='utf-8').read()
if MARK in src:
    print('Schon eingebaut.')
    sys.exit(0)
backup = f'{P}.bak-{time.strftime("%Y%m%d-%H%M%S")}'
shutil.copy2(P, backup)
src = src.replace('from flask import Flask, abort, g, jsonify, request, send_file, send_from_directory',
                  'from flask import Flask, Response, abort, g, jsonify, request, send_file, send_from_directory, stream_with_context', 1)
ROUTE = f'''
{MARK}
CLAUDE_SOCK = '/run/ma-claude/bridge.sock'


@app.post('/api/claude')
def claude_chat():
    """Chat mit Claude auf dem Server (nur Admin). Streamt JSON-Zeilen der Claude-Bruecke."""
    if not g.admin:
        abort(403)
    body = request.get_json()
    req = {{k: body.get(k) for k in ('prompt', 'session', 'dir', 'mode', 'model')}}

    def generate():
        import select as _select
        try:
            with socket.socket(socket.AF_UNIX) as sock:
                sock.settimeout(5)
                sock.connect(CLAUDE_SOCK)
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
            yield b'{{"type":"bridge_error","error":"Claude-Bruecke nicht erreichbar"}}\\n'

    return Response(stream_with_context(generate()), mimetype='application/x-ndjson', headers={{'X-Accel-Buffering': 'no'}})
{MARK}-ENDE

'''
anchor = "if __name__ == '__main__':"
if anchor not in src:
    print('Anker nicht gefunden, nichts geaendert.')
    sys.exit(1)
src = src.replace(anchor, ROUTE.lstrip('\n') + '\n' + anchor, 1)
open(P, 'w', encoding='utf-8').write(src)
try:
    py_compile.compile(P, doraise=True)
except Exception as exc:
    shutil.copy2(backup, P)
    print('Pruefung fehlgeschlagen, zurueckgesetzt:', exc)
    sys.exit(1)
print('Eingebaut. Sicherung:', backup)
