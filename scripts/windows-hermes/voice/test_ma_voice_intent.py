"""Tests fuer /intent (PRIO2 N1): Absichtserkennung ueber das geladene Qwen, strikt validiert, sonst 5xx -> Portal nutzt Satzmuster."""
import json, os, pathlib, tempfile, threading, unittest, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TMP = tempfile.mkdtemp()
TOKEN = pathlib.Path(TMP) / 'token'
TOKEN.write_text('test-token-123', encoding='utf-8')
os.environ['MA_VOICE_TOKEN_FILE'] = str(TOKEN)
os.environ['MA_VOICE_PORT'] = '18797'
import ma_voice_service as S

STATE = {'loaded': True, 'reply': '{"intent": "submit", "text": "Serverlogs zusammenfassen"}', 'last': None}


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
    req = urllib.request.Request('http://127.0.0.1:18797' + path, data=json.dumps(payload).encode(), method='POST')
    req.add_header('X-Voice-Token', 'test-token-123'); req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b'{}')


class IntentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oll = ThreadingHTTPServer(('127.0.0.1', 0), FakeOllama)
        threading.Thread(target=cls.oll.serve_forever, daemon=True).start()
        S.OLLAMA = 'http://127.0.0.1:%d' % cls.oll.server_address[1]
        cls.srv = ThreadingHTTPServer(('127.0.0.1', 18797), S.Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.oll.shutdown()

    def setUp(self):
        STATE.update(loaded=True, reply='{"intent": "submit", "text": "Serverlogs zusammenfassen"}', last=None)

    def test_valid_intent_uses_same_model_schema_and_context(self):
        code, d = call('/intent', {'text': 'Kannst du mir die Serverlogs zusammenfassen?', 'run': 'Backup der Datenbank'})
        self.assertEqual(code, 200)
        # Auftragstext = Andrews Wortlaut (normalisiert), nicht die Umformulierung des Modells
        self.assertEqual((d['intent'], d['text']), ('submit', 'Kannst du mir die Serverlogs zusammenfassen?'))
        req = STATE['last']
        self.assertEqual(req['model'], S.CHAT_MODEL)                 # kein Modelltausch im Grafikspeicher
        self.assertIs(req['think'], False)
        self.assertEqual(req['options']['temperature'], 0)
        self.assertEqual(req['format']['properties']['intent']['enum'], list(S.INTENTS))
        self.assertIn('Backup der Datenbank', req['messages'][-1]['content'])
        self.assertIn('Serverlogs', req['messages'][-1]['content'])

    def test_no_running_job_is_stated(self):
        call('/intent', {'text': 'Wie weit bist du?', 'run': None})
        self.assertIn('kein laufender Auftrag', STATE['last']['messages'][-1]['content'])

    def test_unknown_intent_is_rejected_not_guessed(self):
        STATE['reply'] = '{"intent": "delete_everything", "text": ""}'
        code, _ = call('/intent', {'text': 'irgendwas', 'run': None})
        self.assertEqual(code, 502)

    def test_garbage_model_output_is_rejected(self):
        STATE['reply'] = 'Okay, the user wants'
        self.assertEqual(call('/intent', {'text': 'irgendwas', 'run': None})[0], 502)

    def test_non_action_text_is_dropped_and_action_text_clipped(self):
        STATE['reply'] = json.dumps({'intent': 'none', 'text': 'soll leer sein'})
        self.assertEqual(call('/intent', {'text': 'Danke', 'run': None})[1]['text'], '')
        STATE['reply'] = json.dumps({'intent': 'revise'})
        self.assertLessEqual(len(call('/intent', {'text': 'nimm lieber Java 25 ' * 24, 'run': 'Build'})[1]['text']), S.INTENT_MAX_TEXT)

    def test_cold_or_gpu_busy_returns_503(self):
        STATE['loaded'] = False
        orig = S.gpu_used_mib
        S.gpu_used_mib = lambda: 4800
        try:
            S._warm['state'] = 'off'
            self.assertEqual(call('/intent', {'text': 'Wie weit bist du?', 'run': None})[0], 503)
        finally:
            S.gpu_used_mib = orig

    def test_bad_input_400(self):
        for p in ({}, {'text': ''}, {'text': 'x' * 501}, {'text': 'ok', 'run': 5}, {'text': 'ok', 'run': 'y' * 301}):
            self.assertEqual(call('/intent', p)[0], 400, p)

    def test_requires_token(self):
        req = urllib.request.Request('http://127.0.0.1:18797/intent', data=b'{"text":"x"}', method='POST')
        req.add_header('Content-Type', 'application/json')
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(e.exception.code, 401)


if __name__ == '__main__':
    unittest.main()
