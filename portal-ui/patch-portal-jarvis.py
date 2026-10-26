#!/usr/bin/python3
"""Fuegt /api/jarvis in /opt/ma-home/portal.py ein: JARVIS V16 im Portal (nur Admin, nur Zulassungsliste, Weiterleitung an die Claude-Bruecke).
Idempotent, mit Sicherung und Pruefung. Als root ausfuehren. Aufgerufen von deploy-ui.sh.
Gegenstuecke: server/claude-bridge/ma-claude-bridge.py (op 'jarvis' -> jarvis_cli.py), portal-ui/web/app.js (Reiter JARVIS), docs/jarvis/PORTAL.md."""
import py_compile
import shutil
import sys
import time

P = sys.argv[1] if len(sys.argv) > 1 else '/opt/ma-home/portal.py'
MARK = '# --- MA-JARVIS ---'
END = '# --- MA-CLAUDE-BRIDGE ----ENDE'
ROUTE = f'''{MARK}
@app.post('/api/jarvis')
def jarvis_api():
    """JARVIS V16 (nur Admin): submit, list, status, events, result, cancel, approve, usage, caps, learned, meta, kill, forget."""
    if not g.admin:
        abort(403)
    body = request.get_json(silent=True) or {{}}
    cmd = body.get('cmd')
    if cmd not in ('submit', 'list', 'status', 'events', 'result', 'cancel', 'approve', 'usage', 'caps', 'learned', 'meta', 'kill', 'forget'):
        abort(400)
    try:
        since, limit = int(body.get('since') or 0), int(body.get('limit') or 20)
    except (TypeError, ValueError):
        abort(400)
    req = {{'op': 'jarvis', 'cmd': cmd, 'user': g.user, 'job': str(body.get('job') or '')[:40], 'since': since, 'limit': limit,
           'request': str(body.get('request') or '')[:8000], 'step': str(body.get('step') or '')[:60], 'answer': str(body.get('answer') or '')[:2000],
           'client_id': str(body.get('client_id') or '')[:60], 'state': str(body.get('state') or '')[:3], 'kind': str(body.get('kind') or '')[:10], 'ident': str(body.get('ident') or '')[:80]}}
    try:
        with socket.socket(socket.AF_UNIX) as sock:
            sock.settimeout(45)
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
open(P, 'w', encoding='utf-8', newline='\n').write(src.replace(END, ROUTE + END, 1))
try:
    py_compile.compile(P, doraise=True)
except Exception as exc:
    shutil.copy2(backup, P)
    print('Pruefung fehlgeschlagen, zurueckgesetzt:', exc)
    sys.exit(1)
print('Eingebaut. Sicherung:', backup)
