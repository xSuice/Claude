"""Tests für die Server-seitigen Sprach-Skripte (Hermes-Command-Provider -> lokale KI auf dem PC über den Sprach-Tunnel)."""
import json, os, subprocess, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
TMP = Path(tempfile.mkdtemp())
(TMP / 'tok').write_text('voice-tok', encoding='utf-8')
SEEN = {}


class Voice(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(n)
        SEEN.update(path=self.path, tok=self.headers.get('X-Voice-Token'), ctype=self.headers.get('Content-Type'), body=body)
        if self.path == '/stt':
            out, ctype = json.dumps({'text': 'hallo welt'}).encode(), 'application/json'
        else:
            out, ctype = b'RIFFxxxxWAVE', 'audio/wav'
        code = 503 if SEEN.get('fail') else 200
        self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(out))); self.end_headers(); self.wfile.write(out)


SRV = ThreadingHTTPServer(('127.0.0.1', 0), Voice)
threading.Thread(target=SRV.serve_forever, daemon=True).start()
ENV = dict(os.environ, MA_VOICE_URL='http://127.0.0.1:%d' % SRV.server_address[1], MA_VOICE_TOKEN_FILE=str(TMP / 'tok'))


def run(script, *args):
    return subprocess.run([sys.executable, str(HERE / script), *args], capture_output=True, text=True, env=ENV, timeout=30)


class Scripts(unittest.TestCase):
    def test_stt_posts_audio_with_token_and_writes_text(self):
        SEEN.clear()
        a = TMP / 'a.ogg'; a.write_bytes(b'OggSdata'); o = TMP / 'o.txt'
        r = run('stt_pc.py', str(a), str(o))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(o.read_text(encoding='utf-8'), 'hallo welt')
        self.assertEqual((SEEN['path'], SEEN['tok'], SEEN['ctype'], SEEN['body']), ('/stt', 'voice-tok', 'audio/ogg', b'OggSdata'))

    def test_stt_unknown_extension_and_service_down_fail_cleanly(self):
        a = TMP / 'a.xyz'; a.write_bytes(b'x')
        self.assertNotEqual(run('stt_pc.py', str(a), str(TMP / 'o2.txt')).returncode, 0)
        a2 = TMP / 'b.wav'; a2.write_bytes(b'x')
        bad = dict(ENV, MA_VOICE_URL='http://127.0.0.1:9')
        r = subprocess.run([sys.executable, str(HERE / 'stt_pc.py'), str(a2), str(TMP / 'o3.txt')], capture_output=True, text=True, env=bad, timeout=30)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((TMP / 'o3.txt').exists())

    def test_tts_posts_text_and_writes_wav(self):
        SEEN.clear()
        t = TMP / 't.txt'; t.write_text('Guten Morgen Andrew', encoding='utf-8'); o = TMP / 'o.wav'
        r = run('tts_pc.py', str(t), str(o))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(o.read_bytes()[:4], b'RIFF')
        self.assertEqual(json.loads(SEEN['body'])['text'], 'Guten Morgen Andrew')
        self.assertEqual(SEEN['tok'], 'voice-tok')


if __name__ == '__main__':
    unittest.main()
