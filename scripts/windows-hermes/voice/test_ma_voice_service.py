import io, json, os, pathlib, tempfile, threading, unittest, urllib.request, urllib.error, wave

TMP = tempfile.mkdtemp()
TOKEN = pathlib.Path(TMP) / 'token'
TOKEN.write_text('test-token-123', encoding='utf-8')
os.environ['MA_VOICE_TOKEN_FILE'] = str(TOKEN)
os.environ['MA_VOICE_PORT'] = '18799'
import ma_voice_service as S
from http.server import ThreadingHTTPServer


def call(path, body=None, token='test-token-123', ctype='application/json'):
    req = urllib.request.Request('http://127.0.0.1:18799' + path, data=body, method='POST' if body is not None else 'GET')
    if token:
        req.add_header('X-Voice-Token', token)
    req.add_header('Content-Type', ctype)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.headers.get('Content-Type'), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('Content-Type'), e.read()


class VoiceServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(('127.0.0.1', 18799), S.Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_token_required_and_compared(self):
        self.assertFalse(S.check_token('', ''))
        self.assertFalse(S.check_token('abc', 'abd'))
        self.assertEqual(call('/health', token=None)[0], 401)
        self.assertEqual(call('/health', token='wrong')[0], 401)
        self.assertEqual(call('/health')[0], 200)

    def test_rejects_bad_input(self):
        self.assertEqual(call('/stt', b'xx', ctype='text/plain')[0], 415)
        self.assertEqual(call('/tts', json.dumps({'text': ''}).encode())[0], 400)
        self.assertEqual(call('/tts', json.dumps({'text': 'a' * 2000}).encode())[0], 400)

    def test_real_tts_then_stt_roundtrip(self):
        code, ctype, wav = call('/tts', json.dumps({'text': 'Hallo Andre, heute ist ein ruhiger Abend.'}).encode())
        self.assertEqual(code, 200)
        self.assertEqual(ctype, 'audio/wav')
        with wave.open(io.BytesIO(wav)) as w:
            self.assertGreater(w.getnframes() / w.getframerate(), 1.0)
        code, _, body = call('/stt', wav, ctype='audio/wav')
        self.assertEqual(code, 200)
        text = json.loads(body)['text'].lower()
        self.assertIn('abend', text)

    def test_wakeword_name_is_recognized(self):
        _, _, wav = call('/tts', json.dumps({'text': 'Hey Jarvis, erzähl mir einen Witz.'}).encode())
        code, _, body = call('/stt', wav, ctype='audio/wav')
        self.assertEqual(code, 200)
        self.assertIn('jarvis', json.loads(body)['text'].lower())


if __name__ == '__main__':
    unittest.main()
