"""V9 controlled self-improvement tests on a throwaway git repo. Offline, no Claude."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain_core import Brain
from improve import Improver

PY = sys.executable
ACTIONS = {'actions': {
    'unit': {'argv': [PY, '-m', 'unittest', 'discover', '-s', 'tests', '-q'], 'cwd': '.', 'timeout': 60},
    'not-broken': {'argv': [PY, '-c', "import os,sys;sys.exit(1 if os.path.exists('BREAK') else 0)"], 'cwd': '.'}}}


def sh(repo, *a):
    return subprocess.run(['git', *a], cwd=repo, check=True, capture_output=True, text=True).stdout


class ImproveTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.dir = Path(t.name); self.repo = self.dir / 'repo'; (self.repo / 'tests').mkdir(parents=True)
        (self.repo / 'calc.py').write_text('def add(a, b):\n    return a - b\n')
        (self.repo / 'tests' / 'test_calc.py').write_text(
            'import sys, unittest\nsys.path.insert(0, ".")\nfrom calc import add\n'
            'class T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2, 2), 4)\n')
        sh(self.repo, 'init', '-q'); sh(self.repo, 'add', '.')
        sh(self.repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'init')
        self.brain = Brain(self.dir / 'b.db', 'person-a', {'ma-home'})

    def patch(self, rel, text):
        f = self.repo / rel; old = f.read_text(); f.write_text(text)
        p = sh(self.repo, 'diff'); f.write_text(old)
        return p

    def imp(self, **kw):
        return Improver(self.brain, ACTIONS, self.repo, **kw)

    def test_improved_promote_and_rollback(self):
        fix = self.patch('calc.py', 'def add(a, b):\n    return a + b\n')
        r = self.imp().trial('ma-home', fix, ['unit'], 'fix add')
        self.assertEqual(r['verdict'], 'improved')
        self.assertFalse(r['results']['baseline']['unit']['ok']); self.assertTrue(r['results']['candidate']['unit']['ok'])
        self.assertIn('a - b', (self.repo / 'calc.py').read_text())  # trial never touches the real repo
        self.assertEqual(sh(self.repo, 'worktree', 'list').count('\n'), 1)  # worktrees cleaned up
        with self.assertRaises(PermissionError):
            self.imp().promote(r['trial'])  # promotion is off by default
        p = self.imp(allow_promote=True).promote(r['trial'])
        self.assertEqual(p['status'], 'promoted'); self.assertIn('a + b', (self.repo / 'calc.py').read_text())
        rb = self.imp(allow_promote=True).rollback(r['trial'])
        self.assertEqual(rb['status'], 'rolled_back'); self.assertIn('a - b', (self.repo / 'calc.py').read_text())
        reg = self.imp().register()
        self.assertEqual((reg[0]['verdict'], reg[0]['status']), ('improved', 'rolled_back'))

    def test_rejected_and_protected_tests(self):
        bad = self.patch('calc.py', 'def add(a, b):\n    return a * 3\n')
        self.assertEqual(self.imp().trial('ma-home', bad, ['unit'], 'worse')['verdict'], 'rejected')
        cheat = self.patch('tests/test_calc.py', 'import unittest\n')
        r = self.imp().trial('ma-home', cheat, ['unit'], 'weaken tests')
        self.assertEqual(r['verdict'], 'invalid'); self.assertIn('tests/test_calc.py', r['results']['paths'])
        with self.assertRaises(PermissionError):
            self.imp(allow_promote=True).promote(r['trial'])

    def test_neutral_needs_flag_and_stale_head_refused(self):
        fix = self.patch('calc.py', 'def add(a, b):\n    return a + b\n')
        (self.repo / 'calc.py').write_text('def add(a, b):\n    return a + b\n')
        sh(self.repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qam', 'fix')
        doc = self.patch('calc.py', '# addition\ndef add(a, b):\n    return a + b\n')
        r = self.imp().trial('ma-home', doc, ['unit'], 'comment')
        self.assertEqual(r['verdict'], 'neutral')
        with self.assertRaises(PermissionError):
            self.imp(allow_promote=True).promote(r['trial'])
        (self.repo / 'x.py').write_text('x = 1\n'); sh(self.repo, 'add', 'x.py')
        sh(self.repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'later')
        with self.assertRaises(PermissionError):
            self.imp(allow_promote=True, allow_neutral=True).promote(r['trial'])
        self.assertTrue(fix)

    def test_post_promotion_check_failure_reverts(self):
        fix = self.patch('calc.py', 'def add(a, b):\n    return a + b\n')
        r = self.imp().trial('ma-home', fix, ['unit', 'not-broken'], 'fix add')
        self.assertEqual(r['verdict'], 'improved')
        (self.repo / 'BREAK').write_text('only in production')  # untracked: differs from the worktree
        p = self.imp(allow_promote=True).promote(r['trial'])
        self.assertEqual(p['status'], 'reverted'); self.assertIn('a - b', (self.repo / 'calc.py').read_text())

    def test_limits_and_bad_input(self):
        fix = self.patch('calc.py', 'def add(a, b):\n    return a + b\n')
        imp = self.imp(max_trials_per_day=1)
        imp.trial('ma-home', fix, ['unit'], 'one')
        with self.assertRaises(PermissionError):
            imp.trial('ma-home', fix, ['unit'], 'two')
        with self.assertRaises(ValueError):
            self.imp().trial('ma-home', fix, ['rm'], 'x y z')
        with self.assertRaises(PermissionError):
            self.imp().trial('other', fix, ['unit'], 'x y z')
        r = self.imp(max_trials_per_day=5).trial('ma-home', 'not a patch\n', ['unit'], 'garbage')
        self.assertEqual(r['verdict'], 'invalid')


if __name__ == '__main__':
    unittest.main()
