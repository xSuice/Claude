import unittest
import importlib

class EgressTests(unittest.TestCase):
    def test_only_exact_provider_connect_allowed(self):
        try:
            m = importlib.import_module('egress_guard')
        except ImportError:
            self.fail('egress_guard implementation missing')
        self.assertEqual(m.authority('CONNECT dialagram.me:443 HTTP/1.1'), 'dialagram.me')
        self.assertEqual(m.authority('CONNECT api.kimi.ai:443 HTTP/1.1'), 'api.kimi.ai')
        for value in ['CONNECT 127.0.0.1:443 HTTP/1.1', 'CONNECT localhost:443 HTTP/1.1',
                      'CONNECT dialagram.me.evil.com:443 HTTP/1.1', 'CONNECT dialagram.me:80 HTTP/1.1',
                      'GET http://dialagram.me/ HTTP/1.1', 'CONNECT api.kimi.ai@127.0.0.1:443 HTTP/1.1']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.authority(value)

class AddressTests(unittest.TestCase):
    def test_no_private_or_mixed_dns_answers(self):
        import egress_guard as m
        self.assertTrue(hasattr(m, 'public_addresses'), 'DNS policy missing')
        self.assertEqual(m.public_addresses(['1.1.1.1']), ['1.1.1.1'])
        for ips in [[], ['127.0.0.1'], ['192.168.0.111'], ['169.254.169.254'], ['::1'], ['1.1.1.1', '10.0.0.1']]:
            with self.subTest(ips=ips), self.assertRaises(ValueError):
                m.public_addresses(ips)

class ProxyTests(unittest.TestCase):
    def test_denied_connect_returns_403_without_upstream(self):
        import egress_guard as m
        import socket
        import tempfile
        from pathlib import Path
        self.assertTrue(hasattr(m, 'start_proxy'), 'proxy missing')
        with tempfile.TemporaryDirectory() as td:
            path = str(Path(td) / 'proxy.sock')
            server = m.start_proxy(path)
            try:
                with socket.socket(socket.AF_UNIX) as s:
                    s.settimeout(3)
                    s.connect(path)
                    s.sendall(b'CONNECT 127.0.0.1:18765 HTTP/1.1\r\n\r\n')
                    self.assertIn(b'403', s.recv(1024))
            finally:
                server.shutdown()
                server.server_close()

if __name__ == '__main__':
    unittest.main()
