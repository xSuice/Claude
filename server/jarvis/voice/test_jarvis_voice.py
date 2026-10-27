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


if __name__ == '__main__':
    unittest.main()
