"""Tests für ma-route-ask.py: Antwort im Claude-Format, Rückfall auf Claude im selben Auftrag."""
import json, os, subprocess, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(os.environ.get('ROUTE_DIR', str(Path(__file__).resolve().parent.parent)))
HELPER = HERE / 'ma-route-ask.py'
TMP = Path(tempfile.mkdtemp())
(TMP / 'tok').write_text('tok-123', encoding='utf-8')
FAKE_CLAUDE = TMP / 'fake_claude.py'
FAKE_CLAUDE.write_text('import json,sys\np=sys.stdin.read()\nprint(json.dumps({"type":"result","is_error":False,"result":"CLAUDE:"+p}))\n', encoding='utf-8')
MODE = {'code': 200, 'seen': None}


class Recv(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0)
        MODE['seen'] = (self.headers.get('X-Ask-Token'), json.loads(self.rfile.read(n)))
        body = json.dumps({'answer': 'Rolle sagt: SSH mit Schlüssel', 's': 12.3} if MODE['code'] == 200 else {'error': 'x'}).encode()
        self.send_response(MODE['code']); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)


SRV = ThreadingHTTPServer(('127.0.0.1', 0), Recv)
threading.Thread(target=SRV.serve_forever, daemon=True).start()


def run(receiver=None, ctx='Vorher: X'):
    env = dict(os.environ, MA_ROUTE_RECEIVER=receiver or 'http://127.0.0.1:%d' % SRV.server_address[1],
               MA_ROUTE_TOKEN_FILE=str(TMP / 'tok'), MA_ROUTE_CTX=ctx, MA_ROUTE_TIMEOUT='5',
               MA_ROUTE_CLAUDE_ARGS=json.dumps([sys.executable, str(FAKE_CLAUDE)]))
    r = subprocess.run([sys.executable, str(HELPER), 'jarvis-security', 'jarvis-security · Nexum'], input='Wie sichere ich SSH ab?',
                       capture_output=True, text=True, env=env, timeout=30, encoding='utf-8')
    return r.returncode, [json.loads(l) for l in r.stdout.splitlines() if l.strip()]


class Helper(unittest.TestCase):
    def test_answer_in_claude_stream_format(self):
        MODE['code'] = 200
        code, ev = run()
        self.assertEqual(code, 0)
        self.assertEqual(ev[0]['message']['content'][0]['name'], 'Weiterleitung')
        self.assertEqual(ev[1]['event']['delta']['text'], 'Rolle sagt: SSH mit Schlüssel')
        self.assertEqual((ev[-1]['type'], ev[-1]['is_error'], ev[-1]['result']), ('result', False, 'Rolle sagt: SSH mit Schlüssel'))
        tok, body = MODE['seen']
        self.assertEqual(tok, 'tok-123')
        self.assertEqual(body, {'target': 'jarvis-security', 'message': 'Wie sichere ich SSH ab?', 'context': 'Vorher: X'})

    def test_role_error_falls_back_to_claude_in_same_job(self):
        for c in (504, 502, 401):
            MODE['code'] = c
            code, ev = run()
            self.assertEqual(code, 0, c)
            self.assertIn('Claude übernimmt', ev[1]['event']['delta']['text'])
            self.assertEqual(ev[-1]['result'], 'CLAUDE:Wie sichere ich SSH ab?')

    def test_pc_off_falls_back(self):
        code, ev = run(receiver='http://127.0.0.1:9')
        self.assertIn('nicht erreichbar', ev[1]['event']['delta']['text'])
        self.assertEqual(ev[-1]['result'], 'CLAUDE:Wie sichere ich SSH ab?')


if __name__ == '__main__':
    unittest.main()
