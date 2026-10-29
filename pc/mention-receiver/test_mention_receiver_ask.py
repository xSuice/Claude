"""Tests für POST /api/bot/ask (Router: Frage an eine Hermes-Rolle mit Rückantwort). Ruft eine Hermes-Attrappe auf."""
import json, os, sys, tempfile, threading, time, unittest, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
TMP = Path(tempfile.mkdtemp())
(TMP / 'profiles' / 'jarvis-security').mkdir(parents=True)
(TMP / 'profiles' / 'kimi-supervisor').mkdir(parents=True)
(TMP / 'profiles' / 'privat-bot').mkdir(parents=True)
FAKE = TMP / 'fake_hermes.py'
FAKE.write_text('import json, sys, time\n'
                'a = sys.argv[1:]\n'
                'q = a[a.index("-q") + 1]\n'
                'if "SCHLAF" in q: time.sleep(5)\n'
                'if "KAPUTT" in q: sys.exit(3)\n'
                'print("ANTWORT " + json.dumps(a, ensure_ascii=False))\n'
                'print()\n'
                'print("session_id: local-abc")\n', encoding='utf-8')
(TMP / 'ask-token.txt').write_text('test-token-1234567890', encoding='utf-8')
os.environ.update({'MA_HERMES_CMD': json.dumps([sys.executable, str(FAKE)]), 'MA_HERMES_ROOT': str(TMP),
                   'MA_ASK_TOKEN_FILE': str(TMP / 'ask-token.txt'), 'MA_ASK_TIMEOUT': '2', 'MA_RECEIVER_LOG': str(TMP / 'r.log')})
sys.path.insert(0, str(HERE))
import mention_receiver as R  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402

SRV = ThreadingHTTPServer(('127.0.0.1', 0), R.Handler)
threading.Thread(target=SRV.serve_forever, daemon=True).start()
URL = 'http://127.0.0.1:%d' % SRV.server_address[1]


def post(path, body, token='test-token-1234567890'):
    h = {'Content-Type': 'application/json'}
    if token is not None:
        h['X-Ask-Token'] = token
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode(), headers=h, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


class AskTests(unittest.TestCase):
    def test_answer_comes_back_with_restricted_tools(self):
        code, d = post('/api/bot/ask', {'target': 'jarvis-security', 'message': 'Ist Port 8484 offen?', 'context': 'Vorher: Tunnel'})
        self.assertEqual(code, 200, d)
        self.assertTrue(d['answer'].startswith('ANTWORT'))
        self.assertNotIn('session_id', d['answer'])
        argv = json.loads(d['answer'][len('ANTWORT '):])
        self.assertEqual(argv[argv.index('-t') + 1], 'web,skills,memory,session_search')
        for a in ('--oneshot', '-Q'):
            self.assertIn(a, argv)
        self.assertNotIn('--yolo', argv)
        q = argv[argv.index('-q') + 1]
        self.assertIn('Ist Port 8484 offen?', q)
        self.assertIn('nur Kontext', q)          # Kontext ist als Daten markiert
        self.assertIn('Vorher: Tunnel', q)

    def test_token_required(self):
        self.assertEqual(post('/api/bot/ask', {'target': 'jarvis-security', 'message': 'x'}, token=None)[0], 401)
        self.assertEqual(post('/api/bot/ask', {'target': 'jarvis-security', 'message': 'x'}, token='falsch')[0], 401)

    def test_only_allowed_roles(self):
        self.assertEqual(post('/api/bot/ask', {'target': 'privat-bot', 'message': 'x'})[0], 403)
        self.assertEqual(post('/api/bot/ask', {'target': '../etc', 'message': 'x'})[0], 403)
        self.assertEqual(post('/api/bot/ask', {'target': 'kimi-supervisor', 'message': 'Frage'})[0], 200)

    def test_timeout_and_failure_are_clean_errors(self):
        code, d = post('/api/bot/ask', {'target': 'jarvis-security', 'message': 'SCHLAF'})
        self.assertEqual(code, 504, d)
        code, d = post('/api/bot/ask', {'target': 'jarvis-security', 'message': 'KAPUTT'})
        self.assertEqual(code, 502, d)

    def test_empty_message_rejected(self):
        self.assertEqual(post('/api/bot/ask', {'target': 'jarvis-security', 'message': '  '})[0], 400)

    def test_dm_still_works_without_token(self):   # bestehender Server-Poller sendet (noch) ohne Schlüssel
        code, d = post('/api/bot/dm', {'target': 'jarvis-security', 'message': 'hallo'}, token=None)
        self.assertEqual(code, 202, d)


if __name__ == '__main__':
    unittest.main()
