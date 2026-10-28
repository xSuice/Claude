import json, socket, sys, time
def call(req):
    s = socket.socket(socket.AF_UNIX); s.connect('/run/ma-claude/bridge.sock'); s.settimeout(60)
    s.sendall(json.dumps({'op': 'jarvis', 'user': 'andrew', **req}).encode() + b'\n')
    buf = b''
    while not buf.endswith(b'\n'):
        b = s.recv(65536)
        if not b: break
        buf += b
    return json.loads(buf)
sub = call({'cmd': 'submit', 'request': 'E2E-Test Revisionen: schreibe eine Datei hallo.txt mit dem Wort Hallo (Test, wird gleich abgebrochen)', 'client_id': 'e2erev' + str(int(time.time()))})
job = sub['data']['job_id']; print('submit', sub['ok'], job, sub['data']['state'])
rv = call({'cmd': 'revise', 'job': job, 'request': 'Schreibe stattdessen Servus statt Hallo', 'expected': 1})
print('revise', rv['ok'], rv.get('data'))
stale = call({'cmd': 'revise', 'job': job, 'request': 'Veraltete Änderung mit alter Revision', 'expected': 1})
print('revise_stale', stale['ok'], (stale.get('data') or {}).get('error', '')[:90])
st = call({'cmd': 'status', 'job': job})['data']
print('status rev', st['revision'], [(r['revision'], r['by']) for r in st['revisions']], '| request endet:', st['request'][-60:])
cc = call({'cmd': 'cancel', 'job': job}); print('cancel', cc['ok'], cc['data']['state'])
late = call({'cmd': 'revise', 'job': job, 'request': 'Änderung nach Abbruch'})
print('revise_after_cancel', late['ok'], (late.get('data') or {}).get('error', '')[:90])
ev = call({'cmd': 'events', 'job': job})['data']['events']
print('events', [e['kind'] for e in ev])
