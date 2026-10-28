import threading, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from flask import Flask, g
import jarvis_health as H

SAMPLE = '''# HELP monitor_status Monitor Status (1 = UP, 0= DOWN, 2= PENDING, 3= MAINTENANCE)
monitor_status{monitor_id="1",monitor_name="Portal (intern)",monitor_type="http",monitor_url="http://127.0.0.1:18765/healthz",monitor_hostname="null",monitor_port="null"} 1
monitor_status{monitor_id="5",monitor_name="Sprachdienst PC (Tunnel)",monitor_type="http",monitor_url="http://127.0.0.1:18790/health",monitor_hostname="null",monitor_port="null"} 0
monitor_response_time{monitor_id="1",monitor_name="Portal (intern)",monitor_type="http",monitor_url="x",monitor_hostname="null",monitor_port="null"} 12
monitor_response_time{monitor_id="5",monitor_name="Sprachdienst PC (Tunnel)",monitor_type="http",monitor_url="x",monitor_hostname="null",monitor_port="null"} -1
'''


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(SAMPLE.encode())


class HealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(('127.0.0.1', 0), Fake)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        H.METRICS = 'http://127.0.0.1:%d/metrics' % cls.srv.server_address[1]
        app = Flask(__name__)
        cls.admin = {'v': True}

        @app.before_request
        def auth():
            g.admin = cls.admin['v']
        app.register_blueprint(H.health_bp)
        cls.c = app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_parse_and_no_urls(self):
        d = self.c.get('/api/jarvis/health').get_json()
        self.assertTrue(d['ok'])
        self.assertEqual(d['down'], 1)
        self.assertEqual(d['monitors'][0], {'name': 'Sprachdienst PC (Tunnel)', 'status': 'down', 'ms': None})
        self.assertEqual(d['monitors'][1]['ms'], 12)
        self.assertNotIn('127.0.0.1', str(d))

    def test_admin_only(self):
        self.admin['v'] = False
        try:
            self.assertEqual(self.c.get('/api/jarvis/health').status_code, 403)
        finally:
            self.admin['v'] = True

    def test_kuma_down(self):
        old = H.METRICS
        H.METRICS = 'http://127.0.0.1:9/metrics'
        try:
            d = self.c.get('/api/jarvis/health').get_json()
            self.assertFalse(d['ok'])
            self.assertEqual(d['monitors'], [])
        finally:
            H.METRICS = old


if __name__ == '__main__':
    unittest.main()
