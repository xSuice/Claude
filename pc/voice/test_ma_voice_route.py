"""Tests fuer /route (Chat-Router 29.10.): Fachgebiet einer Chat-Nachricht ueber das geladene Qwen, strikt validiert.
Die Sicherheitsregeln (Werkzeuge noetig, privat, Supervisor-Wort) entscheidet die Bruecke auf dem Server, nicht dieses Modell."""
import json, os, pathlib, tempfile, threading, unittest, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TMP = tempfile.mkdtemp()
TOKEN = pathlib.Path(TMP) / 'token'
TOKEN.write_text('test-token-123', encoding='utf-8')
os.environ['MA_VOICE_TOKEN_FILE'] = str(TOKEN)
os.environ['MA_VOICE_PORT'] = '18798'
import ma_voice_service as S

STATE = {'loaded': True, 'reply': '{"fach": "sicherheit"}', 'last': None}


class FakeOllama(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        body = json.dumps({'models': [{'name': S.CHAT_MODEL}] if STATE['loaded'] else []}).encode()
        self.send_response(200); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0); req = json.loads(self.rfile.read(n))
        STATE['last'] = req
        self.send_response(200); self.end_headers()
        self.wfile.write(json.dumps({'message': {'content': STATE['reply']}, 'done': True}).encode())


def call(path, payload):
    req = urllib.request.Request('http://127.0.0.1:18798' + path, data=json.dumps(payload).encode(), method='POST')
    req.add_header('X-Voice-Token', 'test-token-123'); req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b'{}')


class RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oll = ThreadingHTTPServer(('127.0.0.1', 0), FakeOllama)
        threading.Thread(target=cls.oll.serve_forever, daemon=True).start()
        S.OLLAMA = 'http://127.0.0.1:%d' % cls.oll.server_address[1]
        cls.srv = ThreadingHTTPServer(('127.0.0.1', 18798), S.Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.oll.shutdown()

    def setUp(self):
        STATE.update(loaded=True, reply='{"fach": "sicherheit"}', last=None)

    def test_valid_domain_with_same_model_and_schema(self):
        code, d = call('/route', {'text': 'Ist es riskant, Port 8484 ohne Schlüssel offen zu lassen?'})
        self.assertEqual((code, d['fach']), (200, 'sicherheit'))
        req = STATE['last']
        self.assertEqual(req['model'], S.CHAT_MODEL)                       # kein Modelltausch im Grafikspeicher
        self.assertEqual(req['format']['properties']['fach']['enum'], list(S.FAECHER))
        self.assertEqual(req['options']['temperature'], 0)
        self.assertIn('Port 8484', req['messages'][-1]['content'])
        self.assertIn('ms', d)

    def test_every_domain_is_accepted_and_unknown_rejected(self):
        for f in S.FAECHER:
            STATE['reply'] = json.dumps({'fach': f})
            self.assertEqual(call('/route', {'text': 'Frage zu irgendwas'})[1].get('fach'), f)
        STATE['reply'] = '{"fach": "kochen"}'
        self.assertEqual(call('/route', {'text': 'Frage'})[0], 502)
        STATE['reply'] = 'kein json'
        self.assertEqual(call('/route', {'text': 'Frage'})[0], 502)

    def test_cold_model_and_bad_input(self):
        STATE['loaded'] = False
        self.assertEqual(call('/route', {'text': 'Frage'})[0], 503)
        STATE['loaded'] = True
        self.assertEqual(call('/route', {'text': ''})[0], 400)
        self.assertEqual(call('/route', {'text': 'x' * 5000})[0], 200)       # wird gekuerzt, nicht abgelehnt
        self.assertLessEqual(len(STATE['last']['messages'][-1]['content']), S.ROUTE_MAX_TEXT + 50)


if __name__ == '__main__':
    unittest.main()
