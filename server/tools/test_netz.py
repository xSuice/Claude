#!/usr/bin/env python3
"""Tests fuer netz.py: Zulassungsliste, Stufen, Home-Assistant gegen einen lokalen Schein-Server. Aufruf: python test_netz.py"""
import contextlib
import io
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = {'switch.licht': 'off', 'sensor.temp': '21.5', 'switch.router': 'on'}
CALLS = []


class HA(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.headers.get('Authorization') != 'Bearer testtoken':
            return self._send({}, 401)
        eid = self.path.rsplit('/', 1)[-1]
        self._send({'state': STATE[eid]}) if eid in STATE else self._send({}, 404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        CALLS.append((self.path, body))
        STATE[body['entity_id']] = 'on' if self.path.endswith('turn_on') else 'off'
        self._send([])


srv = HTTPServer(('127.0.0.1', 0), HA)
threading.Thread(target=srv.serve_forever, daemon=True).start()
tmp = tempfile.mkdtemp()
tok = os.path.join(tmp, 'tok')
open(tok, 'w').write('testtoken\n')
cfgp = os.path.join(tmp, 'netz.json')
json.dump({'geraete': {'drucker': {'host': '192.168.0.50', 'port': 631, 'stufe': 1, 'info': 'Flur'}},
           'ha': {'url': f'http://127.0.0.1:{srv.server_port}', 'token_datei': tok,
                  'entities': {'switch.licht': {'stufe': 2, 'info': 'Flur'}, 'sensor.temp': {'stufe': 1}, 'switch.router': {'stufe': 3}}}},
          open(cfgp, 'w'))
os.environ['MA_NETZ_CONFIG'] = cfgp
sys.path.insert(0, HERE)
import netz  # noqa: E402


def run(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            code = netz.main(list(argv))
        except SystemExit as exc:
            code = 1
            print(exc)
    return code, buf.getvalue()


results = []


def check(name, cond):
    results.append(cond)
    print(('PASS ' if cond else 'FAIL ') + name)


c, o = run('liste')
check('liste zeigt Geraet und Entities', c == 0 and 'drucker' in o and 'switch.licht' in o)
c, o = run('status', 'unbekannt')
check('status verweigert Geraet ausserhalb der Liste', c == 1 and 'nicht in der Zulassungsliste' in o)
c, o = run('ha-zustand', 'sensor.temp')
check('Zustand lesen', c == 0 and '21.5' in o)
c, o = run('ha-zustand', 'light.fremd')
check('Zustand fremder Entity verweigert', c == 1 and 'nicht in der Zulassungsliste' in o)
c, o = run('ha-schalten', 'switch.licht', 'an')
check('Schalten Stufe 2 klappt, meldet Rueckweg', c == 0 and 'jetzt on' in o and 'ha-schalten switch.licht aus' in o and CALLS[-1][0].endswith('switch/turn_on'))
c, o = run('ha-schalten', 'switch.licht', 'aus')
check('Ausschalten klappt', c == 0 and STATE['switch.licht'] == 'off')
n = len(CALLS)
c, o = run('ha-schalten', 'sensor.temp', 'an')
check('Stufe 1 darf nicht schalten', c == 1 and 'nur lesen' in o and len(CALLS) == n)
c, o = run('ha-schalten', 'switch.router', 'aus')
check('Stufe 3 verweigert mit Hinweis auf Philipp', c == 1 and 'Bestaetigung von Philipp' in o and len(CALLS) == n and STATE['switch.router'] == 'on')
c, o = run('ha-schalten', 'switch.licht', 'vielleicht')
check('ungueltiger Wert verweigert', c == 1 and len(CALLS) == n)
c, o = run('ha-schalten', '../etc', 'an')
check('Entity-Muster wird geprueft', c == 1 and len(CALLS) == n)
check('Host-Muster blockt Optionen', netz.ping('-f') is False and netz.ping('a b') is False)
os.environ['MA_NETZ_CONFIG'] = os.path.join(tmp, 'gibtsnicht.json')
netz.CONFIG = os.environ['MA_NETZ_CONFIG']
c, o = run('liste')
check('ohne Konfiguration: nichts freigegeben', c == 0 and 'Keine Geraete freigegeben' in o)
print(f'\n{sum(results)}/{len(results)} bestanden')
sys.exit(0 if all(results) else 1)
