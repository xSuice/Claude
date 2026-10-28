import sys, unittest, types
sys.modules['signal_push'] = types.SimpleNamespace(send=lambda *a, **k: 1)
import kuma_signal_bridge as B


class BridgeTests(unittest.TestCase):
    def test_down_and_up_render(self):
        k, t, m = B.render({'heartbeat': {'status': 0, 'msg': 'connect ECONNREFUSED'}, 'monitor': {'name': 'Sprachdienst PC'}})
        self.assertEqual(k, 'Sprachdienst PC:down')
        self.assertIn('ausgefallen', t)
        self.assertIn('ECONNREFUSED', m)
        self.assertEqual(B.render({'heartbeat': {'status': 1}, 'monitor': {'name': 'X'}})[0], 'X:up')

    def test_pending_and_maintenance_ignored(self):
        self.assertIsNone(B.render({'heartbeat': {'status': 2}, 'monitor': {'name': 'X'}}))
        self.assertIsNone(B.render({'heartbeat': {'status': 3}, 'monitor': {'name': 'X'}}))

    def test_test_message(self):
        self.assertEqual(B.render({'msg': 'Uptime Kuma Testing'})[0], 'test')

    def test_rate_limit_per_key(self):
        B._last.clear()
        self.assertTrue(B.allowed('a:down', 1000))
        self.assertFalse(B.allowed('a:down', 1100))
        self.assertTrue(B.allowed('a:up', 1100))
        self.assertTrue(B.allowed('a:down', 1700))

    def test_detail_truncated(self):
        m = B.render({'heartbeat': {'status': 0, 'msg': 'x' * 999}, 'monitor': {'name': 'n' * 200}})
        self.assertLessEqual(len(m[2]), 170)
        self.assertLessEqual(len(m[1]), 90)


if __name__ == '__main__':
    unittest.main()
