"""PRIO2 N4: Bruecke uebersetzt remember/memories sicher in CLI-Argumente (Test gegen eine CLI-Attrappe, die argv/Umgebung zurueckgibt)."""
import importlib.machinery, importlib.util, json, os, sys, tempfile, unittest

BRIDGE = os.environ.get('BRIDGE_FILE', '/usr/local/lib/ma-claude-bridge.py')


def load():
    loader = importlib.machinery.SourceFileLoader('bridge_under_test', BRIDGE)
    spec = importlib.util.spec_from_loader('bridge_under_test', loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


class BridgeMemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.B = load()
        d = tempfile.mkdtemp()
        fake = os.path.join(d, 'fake_cli.py')
        with open(fake, 'w') as f:
            f.write('import json, os, sys\nprint(json.dumps({"argv": sys.argv[1:], "via": os.environ.get("MA_JARVIS_VIA")}))\n')
        with open(os.path.join(d, 'portal-users.json'), 'w') as f:
            json.dump({'andrew': 'jarvis.json'}, f)
        open(os.path.join(d, 'jarvis.json'), 'w').write('{}')
        cls.B.JARVIS_PY, cls.B.JARVIS_CFGDIR = fake, d

    def call(self, **req):
        return self.B.jarvis_api({'user': 'andrew', **req})

    def test_remember_maps_text_and_origin(self):
        r = self.call(cmd='remember', request='  Ich   mag  Tee am Morgen ')
        self.assertTrue(r['ok'], r)
        argv = r['data']['argv']
        self.assertEqual(argv[2:], ['remember', '--text', 'Ich mag Tee am Morgen', '--by', 'portal:andrew'])
        self.assertEqual(r['data']['via'], 'bridge')

    def test_remember_rejects_empty_and_too_long(self):
        for t in ('', 'ab', 'x' * 501):
            r = self.call(cmd='remember', request=t)
            self.assertFalse(r['ok'], t)

    def test_memories_is_simple_readonly(self):
        r = self.call(cmd='memories')
        self.assertEqual(r['data']['argv'][2:], ['memories'])

    def test_forget_memory_still_validated(self):
        self.assertEqual(self.call(cmd='forget', kind='memory', ident='abc123')['data']['argv'][2:], ['forget', 'memory', 'abc123'])
        self.assertFalse(self.call(cmd='forget', kind='memory', ident='a b; rm -rf')['ok'])

    def test_unknown_user_gets_nothing(self):
        self.assertFalse(self.B.jarvis_api({'user': 'mallory', 'cmd': 'remember', 'request': 'Ich mag Tee'})['ok'])


if __name__ == '__main__':
    unittest.main()
