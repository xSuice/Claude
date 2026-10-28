"""Tests fuer scripts/git-hooks/pre-commit: blockiert echte Schluessel, laesst Code durch, misst Fehlalarme ueber die Historie.
Aufruf im Repo-Root: python3 scripts/git-hooks/test_pre_commit.py [--history]"""
import importlib.machinery, importlib.util, os, subprocess, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_L = importlib.machinery.SourceFileLoader('hook', os.path.join(HERE, 'pre-commit'))
_S = importlib.util.spec_from_loader('hook', _L)
H = importlib.util.module_from_spec(_S)
_L.exec_module(H)


def diff(path, line):
    return '+++ b/%s\n+%s\n' % (path, line)


class HookTests(unittest.TestCase):
    def test_blocks_real_secrets(self):
        for p, l in [('c.yaml', 'api_key: sk-ant-' + 'A1b2C3d4E5f6G7h8I9j0K'),
                     ('x.sh', 'export GH=ghp_' + 'a' * 10 + 'B1' * 8),
                     ('x.py', 'password = "Hunter2Secure99x"'),
                     ('x.py', "token = 'Zq81mPx0Lw44Rt'"),
                     ('k.pem', '-----BEGIN OPENSSH PRIVATE KEY-----')]:
            self.assertTrue(H.findings(diff(p, l)), l[:30])

    def test_passes_code_and_prose(self):
        for p, l in [('a.py', 'pw = open(PATH).read().strip()'),
                     ('a.sh', 'password=$DB_PASS'),
                     ('a.py', 'password=db_password'),
                     ('a.py', 'token = cfg.token'),
                     ('a.md', 'Token sparen durch lokale Modelle'),
                     ('a.env.template', 'JARVIS_SECRET_KEY="change-me-please-123"')]:
            self.assertFalse(H.findings(diff(p, l)), l)

    def test_test_files_may_hold_canaries(self):
        self.assertFalse(H.findings(diff('server/x/tests/test_scan.py', 'api_key: sk-ant-' + 'A1b2C3d4E5f6G7h8I9j0K')))


def history():
    revs = subprocess.run(['git', 'rev-list', '--all', '--no-merges'], capture_output=True, text=True).stdout.split()
    hits = []
    for r in revs:
        d = subprocess.run(['git', 'show', '-U0', '--no-color', '--format=', r], capture_output=True, text=True, errors='replace').stdout
        f = H.findings(d)
        if f:
            hits.append((r[:7], f))
    print('Historie: %d Commits, %d mit Treffer' % (len(revs), len(hits)))
    for h in hits:
        print('  ', h)


if __name__ == '__main__':
    if '--history' in sys.argv:
        history()
        sys.argv.remove('--history')
    unittest.main()
