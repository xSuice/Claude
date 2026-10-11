#!/usr/bin/python3
"""Fuegt /api/claude/op in /opt/ma-home/portal.py ein (Status, Abbrechen, Sitzungsliste, Anzeigen, Umbenennen).
Idempotent, mit Sicherung und Pruefung. Als root ausfuehren. Aufgerufen von deploy-ui.sh.
Gegenstueck: server/claude-bridge/ma-claude-bridge.py (op), portal-ui/web/app.js (cop). Vault: Server-Claude Variante 2."""
import py_compile
import shutil
import sys
import time

P = sys.argv[1] if len(sys.argv) > 1 else '/opt/ma-home/portal.py'
MARK = '# --- MA-CLAUDE-OPS ---'
END = '# --- MA-CLAUDE-BRIDGE ----ENDE'
ROUTE = f'''{MARK}
@app.post('/api/claude/op')
def claude_op():
    """Verwaltung der Claude-Bruecke (nur Admin): jobs, cancel, sessions, show, rename."""
    if not g.admin:
        abort(403)
    body = request.get_json() or {{}}
    op = body.get('op')
    if op not in ('jobs', 'cancel', 'sessions', 'show', 'rename'):
        abort(400)
    req = {{'op': op, 'id': str(body.get('id') or '')[:40], 'q': str(body.get('q') or '')[:100], 'name': str(body.get('name') or '')[:80]}}
    try:
        with socket.socket(socket.AF_UNIX) as sock:
            sock.settimeout(15)
            sock.connect(CLAUDE_SOCK)
            sock.sendall(json.dumps(req).encode() + b'\\n')
            data = b''
            while not data.endswith(b'\\n') and len(data) < 3_000_000:
                block = sock.recv(65536)
                if not block:
                    break
                data += block
    except OSError:
        return jsonify(type='bridge_error', error='Claude-Bruecke nicht erreichbar'), 502
    return Response(data.strip() or b'{{}}', mimetype='application/json')


'''
src = open(P, encoding='utf-8').read()
if MARK in src:
    print('Schon eingebaut.')
    sys.exit(0)
if END not in src or 'CLAUDE_SOCK' not in src:
    print('Stelle nicht gefunden (erst die Claude-Bruecke einbauen), nichts geaendert.')
    sys.exit(1)
backup = f'{P}.bak-{time.strftime("%Y%m%d-%H%M%S")}'
shutil.copy2(P, backup)
open(P, 'w', encoding='utf-8').write(src.replace(END, ROUTE + END, 1))
try:
    py_compile.compile(P, doraise=True)
except Exception as exc:
    shutil.copy2(backup, P)
    print('Pruefung fehlgeschlagen, zurueckgesetzt:', exc)
    sys.exit(1)
print('Eingebaut. Sicherung:', backup)
