"""V16 Phase E: improvement jobs (Claude proposes a patch, improve.py trial is the gate). Scripted Claude,
throwaway git repo, no promotion. Linux (sandbox) only."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v16_fakes import FakeClaude, make_app, run_until, tmpdir  # noqa: E402

import sandbox  # noqa: E402
from taskengine import validate_plan  # noqa: E402

LINUX = sys.platform == 'linux' and sandbox.available()
PY = sys.executable
ACTIONS = {'actions': {'unit': {'argv': [PY, '-m', 'unittest', 'discover', '-s', 'tests', '-q'], 'cwd': '.', 'timeout': 60}}}
PLAN = {
    'goal': 'Fehler in calc.add beheben (Probelauf vor Freigabe)', 'task_type': 'improve.calc_fix',
    'match_keywords': ['calc', 'add', 'fehler'],
    'deliverables': [{'path': 'improve-trial.json', 'description': 'Ergebnis des Probelaufs',
                      'checks': [{'type': 'contains', 'value': 'improved'}]}],
    'steps': [
        {'id': 's1', 'title': 'Patch schreiben', 'kind': 'claude', 'instructions': 'Schreibe patch.diff mit der Korrektur ...',
         'outputs': ['patch.diff'], 'deps': []},
        {'id': 's2', 'title': 'Probelauf', 'kind': 'improve', 'patch': 'patch.diff', 'description': 'add korrigieren', 'deps': ['s1']}]}


def sh(repo, *a):
    return subprocess.run(['git', *a], cwd=repo, check=True, capture_output=True, text=True).stdout


class Base(unittest.TestCase):
    def setUp(self):
        self.t = tmpdir(self)
        self.repo = self.t / 'repo'
        (self.repo / 'tests').mkdir(parents=True)
        (self.repo / 'calc.py').write_text('def add(a, b):\n    return a - b\n')
        (self.repo / 'tests' / 'test_calc.py').write_text(
            'import sys, unittest\nsys.path.insert(0, ".")\nfrom calc import add\n'
            'class T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2, 2), 4)\n')
        sh(self.repo, 'init', '-q')
        sh(self.repo, 'add', '.')
        sh(self.repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'init')
        (self.t / 'actions.json').write_text(json.dumps(ACTIONS))
        self.cfg = {'improve': {'enabled': True, 'repo': str(self.repo), 'actions': str(self.t / 'actions.json'), 'checks': ['unit']}}

    def patch(self, rel, text):
        f = self.repo / rel
        old = f.read_text()
        f.write_text(text)
        p = sh(self.repo, 'diff')
        f.write_text(old)
        return p

    def app(self, patch_text, cfg=None):
        steps = {'Patch schreiben': lambda cwd, prompt, n: (cwd / 'patch.diff').write_text(patch_text) and None}
        fake = FakeClaude(PLAN, steps)
        return make_app(self.t, fake, cfg_extra=cfg if cfg is not None else self.cfg), fake


@unittest.skipUnless(LINUX, 'needs Linux with a sandbox backend')
class ImproveJobs(Base):
    def test_good_patch_passes_gate_and_repo_is_untouched(self):
        eng, fake = self.app(self.patch('calc.py', 'def add(a, b):\n    return a + b\n'))
        j = eng.submit('Behebe den Fehler in calc.add', client_id='improve-client-01', options={'improve': True})
        st = run_until(eng, job=j['job_id'])
        self.assertEqual(st['state'], 'done', st)
        self.assertIn('a - b', (self.repo / 'calc.py').read_text())  # gate only, no promotion
        res = json.loads((Path(st['results']) / 'improve-trial.json').read_text())
        self.assertEqual(res['verdict'], 'improved')
        with eng.brain.connection() as c:
            row = c.execute('SELECT verdict, status FROM improvement_trials').fetchone()
        self.assertEqual((row['verdict'], row['status']), ('improved', 'recorded'))
        self.assertEqual(sh(self.repo, 'worktree', 'list').count('\n'), 1)
        self.assertIn('VERBESSERUNGSAUFTRAG', next(c['prompt'] for c in fake.calls if c['planning']))

    def test_planner_hint_only_in_improvement_jobs(self):
        eng, fake = self.app('x')
        eng.submit('Schreibe einen kurzen Text über Katzen', client_id='improve-client-07')
        run_until(eng, rounds=3)
        self.assertNotIn('VERBESSERUNGSAUFTRAG', next(c['prompt'] for c in fake.calls if c['planning']))

    def test_patch_on_protected_path_never_passes(self):
        cheat = self.patch('tests/test_calc.py', 'import unittest\n')
        eng, fake = self.app(cheat)
        j = eng.submit('Behebe den Fehler in calc.add', client_id='improve-client-02', options={'improve': True})
        st = run_until(eng, job=j['job_id'], rounds=60)
        self.assertNotEqual(st['state'], 'done', st)
        with eng.brain.connection() as c:
            verdicts = {r['verdict'] for r in c.execute('SELECT verdict FROM improvement_trials')}
        self.assertEqual(verdicts, {'invalid'})
        self.assertIn('assertEqual(add(2, 2), 4)', (self.repo / 'tests' / 'test_calc.py').read_text())

    def test_rejected_patch_leaves_no_result_file_and_job_is_not_done(self):
        eng, fake = self.app(self.patch('calc.py', 'def add(a, b):\n    return a * 3\n'))
        j = eng.submit('Behebe den Fehler in calc.add', client_id='improve-client-08', options={'improve': True})
        st = run_until(eng, job=j['job_id'], rounds=60)
        self.assertNotEqual(st['state'], 'done', st)
        self.assertFalse((Path(eng.work_root) / j['job_id'] / 'improve-trial.json').exists())
        with eng.brain.connection() as c:
            self.assertEqual({r['verdict'] for r in c.execute('SELECT verdict FROM improvement_trials')}, {'rejected'})

    def test_human_approval_step_shows_trial_summary_and_waits(self):
        plan = copy.deepcopy(PLAN)
        plan['steps'].append({'id': 's3', 'title': 'Freigabe durch Philipp', 'kind': 'human',
                              'question': 'Soll der geprüfte Patch eingespielt werden?', 'deps': ['s2']})
        steps = {'Patch schreiben': lambda cwd, prompt, n: (cwd / 'patch.diff').write_text(
            self.patch('calc.py', 'def add(a, b):\n    return a + b\n')) and None}
        eng = make_app(self.t, FakeClaude(plan, steps), cfg_extra=self.cfg)
        j = eng.submit('Behebe den Fehler in calc.add', client_id='improve-client-09', options={'improve': True})
        st = run_until(eng, job=j['job_id'], rounds=40)
        self.assertEqual(st['state'], 'waiting_approval', st)
        q = next(e for e in eng.events(j['job_id']) if e['kind'] == 'question')['text']
        self.assertIn('improved', q)
        self.assertIn('calc.py', q)
        self.assertIn('+1/-1', q)
        eng.approve(j['job_id'], 's3', 'ja')
        self.assertEqual(run_until(eng, job=j['job_id'])['state'], 'done')
        self.assertIn('a - b', (self.repo / 'calc.py').read_text())  # approval alone never promotes

    def test_not_enabled_means_plan_is_refused(self):
        eng, fake = self.app(self.patch('calc.py', 'def add(a, b):\n    return a + b\n'), cfg={})
        j = eng.submit('Behebe den Fehler in calc.add', client_id='improve-client-03', options={'improve': True})
        st = run_until(eng, job=j['job_id'])
        self.assertEqual(st['state'], 'failed', st)
        with eng.brain.connection() as c:
            # the gate was never even constructed
            self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='improvement_trials'").fetchone())

    def test_without_improve_option_plan_is_refused(self):
        eng, fake = self.app(self.patch('calc.py', 'def add(a, b):\n    return a + b\n'))
        j = eng.submit('Behebe den Fehler in calc.add', client_id='improve-client-04')
        st = run_until(eng, job=j['job_id'])
        self.assertEqual(st['state'], 'failed', st)

    def test_daily_limit_ends_step_without_correction_round(self):
        cfg = {'improve': {**self.cfg['improve'], 'max_trials_per_day': 1}}
        eng, fake = self.app(self.patch('calc.py', 'def add(a, b):\n    return a + b\n'), cfg=cfg)
        first = eng.submit('Behebe den Fehler in calc.add', client_id='improve-client-05', options={'improve': True})
        self.assertEqual(run_until(eng, job=first['job_id'])['state'], 'done')
        second = eng.submit('Behebe den Fehler in calc.add noch einmal', client_id='improve-client-06', options={'improve': True})
        st = run_until(eng, job=second['job_id'], rounds=60)
        self.assertNotEqual(st['state'], 'done', st)
        self.assertEqual(st['fix_rounds'], 0)


class PlanValidation(unittest.TestCase):
    class Reg:
        def usable(self, cap):
            return False

        def get(self, cap, host=None):
            return None

    def check(self, mutate, improve=True):
        plan = copy.deepcopy(PLAN)
        mutate(plan)
        spec = {'data_class': 'internal', 'improve': improve}
        return validate_plan(plan, self.Reg(), spec)

    def test_valid_plan_passes_in_improvement_job(self):
        self.check(lambda p: None)

    def test_refused_outside_improvement_job(self):
        with self.assertRaises(ValueError) as cm:
            self.check(lambda p: None, improve=False)
        self.assertIn('improvement jobs', str(cm.exception))

    def test_patch_must_be_produced_and_diff(self):
        with self.assertRaises(ValueError):
            self.check(lambda p: p['steps'][1].update(patch='other.diff'))
        with self.assertRaises(ValueError):
            self.check(lambda p: p['steps'][1].update(patch='patch.py'))

    def test_plan_cannot_choose_checks(self):
        with self.assertRaises(ValueError):
            self.check(lambda p: p['steps'][1].update(checks=['unit']))

    def test_local_step_cannot_name_the_internal_capability(self):
        with self.assertRaises(ValueError):
            self.check(lambda p: p['steps'][1].update(kind='local', capability='improve.trial', args={}))


if __name__ == '__main__':
    unittest.main()
