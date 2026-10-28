import base64, json, threading, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from flask import Flask, g
import jarvis_voice as V

SEEN = {}


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        SEEN['token'] = self.headers.get('X-Voice-Token')
        self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def do_POST(self):
        n = int(self.headers['Content-Length']); body = self.rfile.read(n)
        SEEN.update(path=self.path, ctype=self.headers.get('Content-Type'), body=body, token=self.headers.get('X-Voice-Token'))
        if self.path == '/tts':
            self.send_response(200); self.send_header('Content-Type', 'audio/wav'); self.end_headers(); self.wfile.write(b'RIFFxx')
        elif self.path == '/chat' and SEEN.get('cold'):
            self.send_response(503); self.send_header('Content-Type', 'application/json'); self.end_headers(); self.wfile.write(b'{"error": "Qwen nicht bereit", "state": "loading"}')
        elif self.path == '/chat':
            self.send_response(200); self.send_header('Content-Type', 'application/x-ndjson'); self.end_headers()
            self.wfile.write(b'{"t": "Hallo "}\n{"t": "Andre."}\n{"done": true}\n')
        elif self.path == '/intent':
            code = SEEN.get('intent_code', 200)
            self.send_response(code); self.send_header('Content-Type', 'application/json'); self.end_headers()
            self.wfile.write(SEEN.get('intent_body', b'{"intent": "submit", "text": "x", "ms": 900}'))
        elif self.path == '/warm':
            self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers(); self.wfile.write(b'{"state": "loading"}')
        else:
            self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers()
            self.wfile.write(json.dumps({'text': 'hallo jarvis'}).encode())


class VoiceProxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(('127.0.0.1', 0), Fake)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        V.UPSTREAM = 'http://127.0.0.1:%d' % cls.srv.server_address[1]
        V._token = lambda: 'tok'
        app = Flask(__name__)
        app.config['MAX_CONTENT_LENGTH'] = 128 * 1024   # wie portal.py
        cls.admin = {'v': True}

        @app.post('/api/other')
        def other():
            from flask import request
            return {'n': len(request.get_json()['audio_b64'])}

        @app.before_request
        def auth():
            g.admin = cls.admin['v']
        app.register_blueprint(V.voice_bp)
        cls.c = app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_non_admin_refused(self):
        self.admin['v'] = False
        try:
            self.assertEqual(self.c.post('/api/voice/tts', json={'text': 'x'}).status_code, 403)
            self.assertEqual(self.c.post('/api/voice/stt', json={'mime': 'audio/webm', 'audio_b64': 'eA=='}).status_code, 403)
        finally:
            self.admin['v'] = True

    def test_stt_forwards_audio_with_token(self):
        r = self.c.post('/api/voice/stt', json={'mime': 'audio/webm;codecs=opus', 'audio_b64': base64.b64encode(b'OggS-audio').decode()})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()['text'], 'hallo jarvis')
        self.assertEqual(SEEN['body'], b'OggS-audio')
        self.assertEqual(SEEN['ctype'], 'audio/webm')
        self.assertEqual(SEEN['token'], 'tok')

    def test_stt_rejects_wrong_type_bad_base64_and_oversize(self):
        self.assertEqual(self.c.post('/api/voice/stt', json={'mime': 'text/plain', 'audio_b64': 'eA=='}).status_code, 415)
        self.assertEqual(self.c.post('/api/voice/stt', json={'mime': 'audio/webm', 'audio_b64': '***'}).status_code, 400)
        big = base64.b64encode(b'x' * (V.MAX_AUDIO + 1)).decode()
        self.assertEqual(self.c.post('/api/voice/stt', json={'mime': 'audio/webm', 'audio_b64': big}).status_code, 413)

    def test_stt_allows_wav_above_global_limit_only_on_this_route(self):
        wav = b'RIFF' + b'\x00' * (400 * 1024)
        body = {'mime': 'audio/wav', 'audio_b64': base64.b64encode(wav).decode()}
        r = self.c.post('/api/voice/stt', json=body)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(SEEN['body'], wav)
        self.assertEqual(SEEN['ctype'], 'audio/wav')
        self.assertEqual(self.c.post('/api/other', json=body).status_code, 413)   # globale Grenze bleibt

    def test_stt_route_limit_still_bounded(self):
        big = base64.b64encode(b'x' * (V.MAX_AUDIO + 300 * 1024)).decode()
        self.assertEqual(self.c.post('/api/voice/stt', json={'mime': 'audio/wav', 'audio_b64': big}).status_code, 413)

    def test_tts_validates_and_returns_audio(self):
        self.assertEqual(self.c.post('/api/voice/tts', json={'text': ''}).status_code, 400)
        r = self.c.post('/api/voice/tts', json={'text': 'Hallo'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.mimetype, 'audio/wav')
        self.assertEqual(r.data, b'RIFFxx')

    def test_pc_offline_gives_503(self):
        old = V.UPSTREAM
        V.UPSTREAM = 'http://127.0.0.1:9'
        try:
            self.assertEqual(self.c.post('/api/voice/tts', json={'text': 'Hallo'}).status_code, 503)
            self.assertFalse(self.c.get('/api/voice/health').get_json()['ok'])
        finally:
            V.UPSTREAM = old


    def test_chat_streams_and_cold_is_503(self):
        SEEN['cold'] = False
        r = self.c.post('/api/voice/chat', json={'messages': [{'role': 'user', 'content': 'Hallo'}]})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Andre.', r.data)
        self.assertEqual(json.loads(SEEN['body'])['messages'][0]['content'], 'Hallo')
        SEEN['cold'] = True
        r = self.c.post('/api/voice/chat', json={'messages': [{'role': 'user', 'content': 'Hallo'}]})
        self.assertEqual(r.status_code, 503)
        SEEN['cold'] = False
        self.assertEqual(self.c.post('/api/voice/chat', json={'messages': []}).status_code, 400)
        self.assertEqual(self.c.post('/api/voice/warm', json={}).get_json()['state'], 'loading')

    def test_chat_admin_only(self):
        self.admin['v'] = False
        try:
            self.assertEqual(self.c.post('/api/voice/chat', json={'messages': [{'role': 'user', 'content': 'x'}]}).status_code, 403)
        finally:
            self.admin['v'] = True


    def test_intent_forwards_and_sanitizes(self):
        SEEN.pop('intent_code', None); SEEN.pop('intent_body', None)
        r = self.c.post('/api/voice/intent', json={'text': 'Sortier die Fotos', 'run': 'Logs'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {'intent': 'submit', 'ms': 900})          # nur Absicht + Zeit, kein Freitext zurück
        self.assertEqual(json.loads(SEEN['body']), {'text': 'Sortier die Fotos', 'run': 'Logs'})
        self.assertEqual(SEEN['token'], 'tok')

    def test_intent_errors_map_to_fallback_codes(self):
        try:
            SEEN['intent_code'], SEEN['intent_body'] = 503, b'{"error": "Qwen nicht bereit"}'
            self.assertEqual(self.c.post('/api/voice/intent', json={'text': 'x'}).status_code, 503)
            SEEN['intent_code'], SEEN['intent_body'] = 200, b'{"intent": "rm_rf"}'
            self.assertEqual(self.c.post('/api/voice/intent', json={'text': 'x'}).status_code, 502)
            SEEN['intent_code'], SEEN['intent_body'] = 500, b'boom'
            self.assertEqual(self.c.post('/api/voice/intent', json={'text': 'x'}).status_code, 503)
        finally:
            SEEN.pop('intent_code', None); SEEN.pop('intent_body', None)

    def test_intent_validates_and_admin_only(self):
        for p in ({}, {'text': ''}, {'text': 'x' * 501}, {'text': 'ok', 'run': 3}, {'text': 'ok', 'run': 'y' * 301}):
            self.assertEqual(self.c.post('/api/voice/intent', json=p).status_code, 400, p)
        self.admin['v'] = False
        try:
            self.assertEqual(self.c.post('/api/voice/intent', json={'text': 'x'}).status_code, 403)
        finally:
            self.admin['v'] = True


if __name__ == '__main__':
    unittest.main()
