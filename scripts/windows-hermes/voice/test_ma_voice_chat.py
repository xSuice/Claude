"""Tests fuer das Gespraechs-LLM (Qwen via Ollama) im PC-Sprachdienst. Ollama/GPU werden simuliert."""
import json, os, pathlib, tempfile, threading, unittest, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TMP = tempfile.mkdtemp()
TOKEN = pathlib.Path(TMP) / 'token'
TOKEN.write_text('test-token-123', encoding='utf-8')
os.environ['MA_VOICE_TOKEN_FILE'] = str(TOKEN)
os.environ['MA_VOICE_PORT'] = '18798'
import ma_voice_service as S

LOADED = {'v': True}


class FakeOllama(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        body = json.dumps({'models': [{'name': S.CHAT_MODEL}] if LOADED['v'] else []}).encode()
        self.send_response(200); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0); req = json.loads(self.rfile.read(n))
        self.send_response(200); self.end_headers()
        if self.path == '/api/chat':
            assert req['messages'][0]['role'] == 'system' and req['think'] is False
            for p in ('Hallo ', 'Andre.'):
                self.wfile.write((json.dumps({'message': {'content': p}, 'done': False}) + '\n').encode())
            self.wfile.write(b'{"done": true}\n')
        else:
            self.wfile.write(b'{}')


def call(path, body=None):
    req = urllib.request.Request('http://127.0.0.1:18798' + path, data=body, method='POST' if body is not None else 'GET')
    req.add_header('X-Voice-Token', 'test-token-123'); req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


class ChatTests(unittest.TestCase):
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

    def test_stream_when_warm(self):
        LOADED['v'] = True
        code, body = call('/chat', json.dumps({'messages': [{'role': 'user', 'content': 'Hallo'}]}).encode())
        self.assertEqual(code, 200)
        lines = [json.loads(l) for l in body.decode().splitlines()]
        self.assertEqual(''.join(l.get('t', '') for l in lines), 'Hallo Andre.')
        self.assertTrue(lines[-1]['done'])

    def test_cold_returns_503_and_gpu_guard(self):
        LOADED['v'] = False
        orig = S.gpu_used_mib
        S.gpu_used_mib = lambda: 4800          # Spiel belegt die GPU
        try:
            S._warm['state'] = 'off'
            code, body = call('/chat', json.dumps({'messages': [{'role': 'user', 'content': 'Hallo'}]}).encode())
            self.assertEqual(code, 503)
            self.assertEqual(json.loads(body)['state'], 'busy')
        finally:
            S.gpu_used_mib = orig; LOADED['v'] = True

    def test_rejects_bad_messages(self):
        for m in ([], [{'role': 'system', 'content': 'x'}], [{'role': 'user', 'content': 'a'}, {'role': 'assistant', 'content': 'b'}], [{'role': 'user', 'content': 'x'}] * 13):
            self.assertEqual(call('/chat', json.dumps({'messages': m}).encode())[0], 400, m)

    def test_state_endpoint(self):
        LOADED['v'] = True
        code, body = call('/chat/state')
        self.assertEqual((code, json.loads(body)['state']), (200, 'warm'))


if __name__ == '__main__':
    unittest.main()
