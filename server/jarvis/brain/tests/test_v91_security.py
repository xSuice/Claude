"""V9.1 security regressions (written before the fixes): patch-path bypasses, isolation of
self-generated code, approval gate for model-bound actions. Offline, no Claude."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain_core import Brain
from improve import Improver
import runner
import sandbox

PY = sys.executable
UNIT = {'argv': [PY, '-m', 'unittest', 'discover', '-s', 'tests', '-q'], 'cwd': '.', 'timeout': 60}
SBX = sandbox.available()


def git(repo, *a, inp=None):
    return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=repo, check=True,
                          capture_output=True, text=True, input=inp).stdout


class Repo(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.dir = Path(t.name); self.repo = self.dir / 'repo'; (self.repo / 'tests').mkdir(parents=True)
        (self.repo / 'calc.py').write_text('def add(a, b):\n    return a - b\n')
        (self.repo / 'tests' / 'test_calc.py').write_text(
            'import sys, unittest\nsys.path.insert(0, ".")\nfrom calc import add\n'
            'class T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2, 2), 4)\n')
        git(self.repo, 'init', '-q'); git(self.repo, 'add', '.'); git(self.repo, 'commit', '-qm', 'init')
        self.brain = Brain(self.dir / 'state' / 'b.db', 'person-a', {'ma-home'})

    def staged_patch(self, fn):
        fn(); git(self.repo, 'add', '-A'); p = git(self.repo, 'diff', '--cached', '--binary')
        git(self.repo, 'reset', '-q', '--hard'); git(self.repo, 'clean', '-qfd')
        return p

    def imp(self, **kw):
        kw.setdefault('max_trials_per_day', 20)
        return Improver(self.brain, {'actions': {'unit': dict(UNIT)}}, self.repo, **kw)

    FIX = 'def add(a, b):\n    return a + b\n'


class PatchPathBypass(Repo):
    def verdict(self, fn):
        return self.imp(require_sandbox=False).trial('ma-home', self.staged_patch(fn), ['unit'], 'probe')

    def test_rename_out_of_protected_is_invalid(self):
        def f():
            (self.repo / 'calc.py').write_text(self.FIX)
            git(self.repo, 'mv', 'tests/test_calc.py', 'moved_test.py')
        r = self.verdict(f)
        self.assertEqual(r['verdict'], 'invalid'); self.assertIn('tests/test_calc.py', r['results']['paths'])

    def test_delete_protected_is_invalid(self):
        self.assertEqual(self.verdict(lambda: (self.repo / 'tests' / 'test_calc.py').unlink())['verdict'], 'invalid')

    def test_symlink_is_invalid(self):
        def f():
            (self.repo / 'calc.py').write_text(self.FIX); (self.repo / 'leak').symlink_to('/etc/passwd')
        r = self.verdict(f)
        self.assertEqual(r['verdict'], 'invalid'); self.assertIn('symlink', r['results']['error'])

    def test_case_variant_of_protected_is_invalid(self):
        def f():
            (self.repo / 'calc.py').write_text(self.FIX)
            (self.repo / 'Tests').mkdir(); (self.repo / 'Tests' / 'x.py').write_text('x=1\n')
        self.assertEqual(self.verdict(f)['verdict'], 'invalid')

    def test_binary_patch_is_invalid(self):
        def f():
            (self.repo / 'calc.py').write_text(self.FIX); (self.repo / 'blob.bin').write_bytes(bytes(range(256)))
        r = self.verdict(f)
        self.assertEqual(r['verdict'], 'invalid'); self.assertIn('binary', r['results']['error'])

    def test_plain_fix_still_improved(self):
        r = self.verdict(lambda: (self.repo / 'calc.py').write_text(self.FIX))
        self.assertEqual(r['verdict'], 'improved')


@unittest.skipUnless(SBX, 'user/mount/net namespaces not available')
class Isolation(Repo):
    def setUp(self):
        super().setUp()
        self.secret = self.dir / 'state' / 'secret.txt'; self.secret.write_text('s')

    def exfil_patch(self):
        code = (f'def add(a, b):\n    try:\n        ok = open({str(self.secret)!r}).read() == "s"\n'
                f'    except OSError:\n        ok = False\n    return a + b if ok else 0\n')
        return self.staged_patch(lambda: (self.repo / 'calc.py').write_text(code))

    def test_candidate_cannot_read_brain_state(self):
        p = self.exfil_patch()
        self.assertEqual(self.imp(require_sandbox=False, sandbox=False).trial('ma-home', p, ['unit'], 'xyz')['verdict'],
                         'improved')  # V9 behaviour: secret was readable
        self.assertEqual(self.imp().trial('ma-home', p, ['unit'], 'xyz')['verdict'], 'rejected')

    def test_sandboxed_run_blocks_write_net_and_secrets(self):
        work = self.dir / 'w'; work.mkdir()
        probe = (f"import os,socket\nr=[]\n"
                 f"try:\n open({str(self.dir / 'outside.txt')!r},'w'); r.append('wrote-outside')\nexcept OSError: pass\n"
                 f"try:\n socket.create_connection(('1.1.1.1',443),timeout=2); r.append('net')\nexcept OSError: pass\n"
                 f"if os.path.exists({str(self.secret)!r}): r.append('secret')\n"
                 f"if os.listdir('/root'): r.append('root-home')\n"
                 f"open('inside.txt','w').write('ok')\nprint(','.join(r) or 'clean')")
        res = runner.run({'argv': [PY, '-c', probe], 'cwd': '.'}, work, sandbox={'hide': [str(self.dir / 'state')]})
        self.assertEqual(res['tail'].strip(), 'clean')
        self.assertTrue((work / 'inside.txt').exists()); self.assertFalse((self.dir / 'outside.txt').exists())

    def test_work_dir_inside_hidden_home_still_works(self):
        home = Path.home()
        with tempfile.TemporaryDirectory(dir=home) as w:
            res = runner.run({'argv': [PY, '-c', "open('a','w').write('1');print(len(__import__('os').listdir('.')))"]},
                             Path(w), sandbox={'hide': []})
            self.assertTrue(res['ok'], res); self.assertTrue((Path(w) / 'a').exists())


class FailClosed(Repo):
    def test_no_sandbox_means_no_trial(self):
        p = self.staged_patch(lambda: (self.repo / 'calc.py').write_text(self.FIX))
        with mock.patch('sandbox.available', return_value=False):
            r = self.imp().trial('ma-home', p, ['unit'], 'xyz')
        self.assertEqual(r['verdict'], 'invalid'); self.assertIn('sandbox', r['results']['error'])


class ApprovalGate(unittest.TestCase):
    """A model (possibly prompt-injected by vault text) may only schedule 'auto' actions directly."""
    def test_mcp_binding_of_non_auto_action_waits_for_admin(self):
        from executive import Executive
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); d = Path(t.name); (d / 'ws').mkdir()
        b = Brain(d / 'b.db', 'person-a', {'ma-home'})
        acts = {'actions': {'touch': {'argv': [PY, '-c', "open('x','w')"]},
                            'safe': {'argv': [PY, '-c', "pass"], 'auto': True},
                            'has-x': {'argv': [PY, '-c', "import os,sys;sys.exit(0 if os.path.exists('x') else 1)"]}}}
        ex = Executive(b, acts, d / 'ws')
        g = b.new_goal('ma-home', 'g', 'r', ['a', 'b'])
        with b.connection() as db:
            s1, s2 = [r[0] for r in db.execute('SELECT id FROM steps WHERE goal_id=? ORDER BY ordinal', (g['goal_id'],))]
        self.assertEqual(ex.bind('ma-home', s1, 'touch', 'has-x', by='mcp')['state'], 'awaiting_approval')
        ex.run_once('ma-home')
        self.assertFalse((d / 'ws' / 'x').exists())
        ex.approve('ma-home', s1)
        ex.run_once('ma-home')
        self.assertTrue((d / 'ws' / 'x').exists())
        self.assertEqual(ex.bind('ma-home', s2, 'safe', 'safe', by='mcp')['state'], 'ready')


if __name__ == '__main__':
    unittest.main()
