"""V9 executive + runner tests. Offline; local python subprocesses only, no Claude."""
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain_core import Brain
import runner
from executive import Executive

PY = sys.executable


def act(code, **kw):
    return {'argv': [PY, '-c', code], 'cwd': '.', 'timeout': kw.pop('timeout', 30), **kw}


def actions(**limits):
    return {'actions': {
        'make': act("open('done.txt','w').write('x')", idempotent=True),
        'has-file': act("import os,sys;sys.exit(0 if os.path.exists('done.txt') else 1)"),
        'count': act("import pathlib;p=pathlib.Path('n.txt');p.write_text(str(int(p.read_text() if p.exists() else 0)+1))"),
        'fail': act("import sys;sys.exit(3)"),
        'leak': act("print('token=abc123secret sk-ant-REALKEYvalue123456')"),
        'slow': act("import time;time.sleep(5)", timeout=1),
        'audit': {'claude_template': 'repo_audit'}},
        'limits': {'max_steps_per_run': 3, 'max_local_runs_per_day': 60, 'max_attempts': 2, **limits}}


class ExecutiveTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.dir = Path(t.name); self.ws = self.dir / 'ws'; self.ws.mkdir()
        self.brain = Brain(self.dir / 'b.db', 'person-a', {'ma-home'})
        self.ex = Executive(self.brain, actions(), self.ws)

    def goal(self, n=1, priority=3):
        g = self.brain.new_goal('ma-home', 'Ziel', 'Ergebnis', [f'Schritt {i}' for i in range(1, n + 1)], priority)
        with self.brain.connection() as db:
            return [r['id'] for r in db.execute('SELECT id FROM steps WHERE goal_id=? ORDER BY ordinal', (g['goal_id'],))], g['goal_id']

    def status(self, step):
        with self.brain.connection() as db:
            return db.execute('SELECT status,attempts FROM steps WHERE id=?', (step,)).fetchone()

    def test_act_check_verify_in_order_and_goal_completes(self):
        (s1, s2), gid = self.goal(2)
        self.ex.bind('ma-home', s1, 'make', 'has-file'); self.ex.bind('ma-home', s2, 'count', 'has-file')
        r = self.ex.run_once('ma-home')
        self.assertEqual([x['step_id'] for x in r['executed']], [s1])  # s2 waits for s1 (ordinal dependency)
        self.assertEqual(self.status(s1)['status'], 'verified')
        self.ex.run_once('ma-home')
        self.assertEqual(self.status(s2)['status'], 'verified')
        with self.brain.connection() as db:
            self.assertEqual(db.execute('SELECT state FROM goals WHERE id=?', (gid,)).fetchone()[0], 'completed')
            self.assertEqual(db.execute("SELECT COUNT(*) FROM episodes WHERE verified=1 AND outcome='success'").fetchone()[0], 2)
        self.assertEqual(self.ex.run_once('ma-home')['executed'], [])  # nothing re-run
        self.assertEqual((self.ws / 'n.txt').read_text(), '1')

    def test_unbound_steps_reported_not_run(self):
        (s1,), _ = self.goal(1)
        self.assertEqual(self.ex.run_once('ma-home')['needs_binding'], [s1])

    def test_failed_check_retries_once_then_blocks_and_learns(self):
        steps = []
        for _ in range(3):
            (s,), _ = self.goal(1); steps.append(s); self.ex.bind('ma-home', s, 'count', 'fail')
        r1 = self.ex.run_once('ma-home')
        self.assertTrue(all(x['state'] == 'ready' for x in r1['executed']))
        self.ex.run_once('ma-home')
        self.assertTrue(all(self.status(s)['status'] == 'blocked' for s in steps))
        self.assertEqual(self.ex.run_once('ma-home')['executed'], [])  # blocked never auto-retried
        self.assertEqual((self.ws / 'n.txt').read_text(), '6')  # 3 steps x 2 attempts, bounded
        sugg = self.brain.tick('ma-home')['new_suggestions']
        self.assertEqual([x['cause'] for x in sugg], ['recurring-failure:action:count'])

    def test_crash_resume_idempotent_and_block_non_idempotent(self):
        (s1,), _ = self.goal(1); (s2,), _ = self.goal(1)
        self.ex.bind('ma-home', s1, 'make', 'has-file'); self.ex.bind('ma-home', s2, 'count', 'has-file')
        with self.brain.connection(True) as db:  # simulate a worker that died mid-run
            db.execute("UPDATE exec_bindings SET state='running',lease_until=? ", (int(time.time()) - 5,))
        r = self.ex.run_once('ma-home')
        self.assertEqual({x['step_id']: x['resumed'] for x in r['reconciled']}, {s1: True, s2: False})
        self.assertEqual(self.status(s1)['status'], 'verified')
        self.assertEqual(self.status(s2)['status'], 'blocked')
        self.assertFalse((self.ws / 'n.txt').exists())  # non-idempotent action not re-run

    def test_crash_after_effect_is_verified_without_rerun(self):
        (s1,), _ = self.goal(1); self.ex.bind('ma-home', s1, 'count', 'has-file')
        with self.brain.connection(True) as db:
            db.execute("UPDATE exec_bindings SET state='running',lease_until=?", (int(time.time()) - 5,))
        (self.ws / 'done.txt').write_text('x')  # the crashed run had finished its work
        r = self.ex.run_once('ma-home')
        self.assertEqual(r['reconciled'][0]['state'], 'done')
        self.assertEqual(self.status(s1)['status'], 'verified')
        self.assertFalse((self.ws / 'n.txt').exists())  # not executed a second time

    def test_live_lease_not_stolen_concurrently(self):
        (s1,), _ = self.goal(1)
        self.ex.bind('ma-home', s1, 'count', 'has-file')
        (self.ws / 'done.txt').write_text('x')
        exs = [Executive(Brain(self.dir / 'b.db', 'person-a', {'ma-home'}), actions(), self.ws) for _ in range(4)]
        ts = [threading.Thread(target=e.run_once, args=('ma-home',)) for e in exs]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual((self.ws / 'n.txt').read_text(), '1')

    def test_pause_and_daily_limit(self):
        (s1,), _ = self.goal(1); self.ex.bind('ma-home', s1, 'make', 'has-file')
        self.ex.loop.set_paused('ma-home', True)
        self.assertTrue(self.ex.run_once('ma-home')['paused'])
        self.ex.loop.set_paused('ma-home', False)
        tight = Executive(self.brain, actions(max_local_runs_per_day=1), self.ws)
        r = tight.run_once('ma-home')
        self.assertEqual(r['skipped'][0]['reason'], 'daily local run limit')
        self.assertFalse((self.ws / 'done.txt').exists())

    def test_step_blocked_by_report_is_not_run(self):
        (s1,), _ = self.goal(1); self.ex.bind('ma-home', s1, 'count', 'has-file')
        self.brain.report_step('ma-home', s1, 'blocked', 'needs owner decision')
        self.assertEqual(self.ex.run_once('ma-home')['executed'], [])
        self.assertFalse((self.ws / 'n.txt').exists())

    def test_bind_validation(self):
        (s1,), _ = self.goal(1)
        with self.assertRaises(ValueError): self.ex.bind('ma-home', s1, 'rm-rf', 'has-file')
        with self.assertRaises(ValueError): self.ex.bind('ma-home', s1, 'make', 'audit')
        other = Executive(Brain(self.dir / 'b.db', 'person-b', {'ma-home'}), actions(), self.ws)
        with self.assertRaises(PermissionError): other.bind('ma-home', s1, 'make', 'has-file')
        with self.assertRaises(PermissionError): self.ex.bind('other', s1, 'make', 'has-file')

    def test_claude_step_needs_queue_then_checked(self):
        from autonomy import Queue, validated
        (s1,), _ = self.goal(1); self.ex.bind('ma-home', s1, 'audit', 'has-file')
        r = self.ex.run_once('ma-home')
        self.assertEqual(r['executed'][0]['reason'], 'claude queue disabled (no cost)')
        cfg = validated({'enabled': True, 'allowed_workspaces': [str(self.ws)], 'db_path': str(self.dir / 'q.db'),
                         'minimum_gap_seconds': 0}, self.dir / 'a.json')
        ex = Executive(self.brain, actions(), self.ws, cfg)
        r = ex.run_once('ma-home')
        job = r['executed'][0]['job_id']; self.assertEqual(r['executed'][0]['state'], 'waiting')
        self.assertEqual(ex.run_once('ma-home')['waiting'][0]['job'], 'queued')  # no Claude started here
        q = Queue(cfg['db_path']); q.claim(cfg); q.finish(job, True, 0, 10, 'audit text')
        (self.ws / 'done.txt').write_text('x')
        self.assertEqual(ex.run_once('ma-home')['waiting'][0]['state'], 'done')
        self.assertEqual(self.status(s1)['status'], 'verified')


class RunnerTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); self.ws = Path(t.name)

    def test_validation_rejects_shells_and_bad_keys(self):
        for a in [{'argv': ['bash', '-c', 'x']}, {'argv': ['/usr/bin/sudo', 'ls']}, {'argv': []},
                  {'argv': ['ls'], 'shell': True}, {'claude_template': 'repo_audit', 'argv': ['x']}]:
            with self.assertRaises(ValueError):
                runner.validate({'actions': {'x': a}})

    def test_cwd_escape_timeout_and_redaction(self):
        with self.assertRaises(PermissionError):
            runner.run(act('pass', cwd='..'), self.ws)
        t0 = time.monotonic(); r = runner.run(act('import time;time.sleep(5)', timeout=1), self.ws)
        self.assertEqual(r['exit'], 124); self.assertLess(time.monotonic() - t0, 4)
        r = runner.run(actions()['actions']['leak'], self.ws)
        self.assertNotIn('abc123secret', r['tail']); self.assertNotIn('REALKEY', r['tail'])
        self.assertEqual(runner.run({'argv': ['does-not-exist-xyz']}, self.ws)['exit'], 127)


if __name__ == '__main__':
    unittest.main()
