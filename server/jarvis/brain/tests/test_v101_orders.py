"""V10.1 order model, kill switch, double start, privileged gate, budget, deadline, cancel,
diagnosis packet and log digest. Offline, no Claude."""
import json
import os
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain_core import Brain
from executive import Executive
from orders import Orders
from daemon import Daemon
from logdigest import digest
import runner

PY = sys.executable


class Base(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.dir = Path(t.name); self.ws = self.dir / 'ws'; self.ws.mkdir()
        self.brain = Brain(self.dir / 'state' / 'b.db', 'person-a', {'ma-home'})
        self.acts = {'actions': {
            'touch': {'argv': [PY, '-c', "open('x','a').write('1')"]},
            'has-x': {'argv': [PY, '-c', "import os,sys;sys.exit(0 if os.path.exists('x') else 1)"], 'auto': True},
            'reboot': {'argv': [PY, '-c', "open('REBOOTED','w')"], 'risk': 'privileged'},
            'diagnose': {'claude_template': 'diagnosis'}, 'ok': {'argv': [PY, '-c', 'pass']}}}
        self.ex = Executive(self.brain, json.loads(json.dumps(self.acts)), self.ws)

    def steps(self, gid):
        with self.brain.connection() as db:
            return [r[0] for r in db.execute('SELECT id FROM steps WHERE goal_id=? ORDER BY ordinal', (gid,))]


class Idempotency(Base):
    def test_same_key_one_goal_even_under_race(self):
        o = Orders(self.brain)
        a = o.open('ma-home', 't', 'r', ['s'], idem_key='anomaly:42')
        self.assertTrue(o.open('ma-home', 't', 'r', ['s'], idem_key='anomaly:42')['duplicate'])
        res = []
        def go():
            res.append(Orders(Brain(self.brain.db_path, 'person-a', {'ma-home'})).open(
                'ma-home', 't', 'r', ['s'], idem_key='anomaly:race'))
        ts = [threading.Thread(target=go) for _ in range(6)]; [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(len({r['goal_id'] for r in res}), 1)
        with self.brain.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM goals').fetchone()[0], 2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM steps').fetchone()[0], 2)  # losers left no orphans
        self.assertFalse(a['duplicate'])


    def test_forced_race_second_process_wins_db_constraint(self):
        """Process 1 passes the duplicate check; before it records its order, process 2 records the same
        key. The UNIQUE constraint must reject process 1, which withdraws its goal without orphans."""
        from unittest import mock
        o1 = Orders(self.brain); o2 = Orders(Brain(self.brain.db_path, 'person-a', {'ma-home'}))
        real_new_goal = self.brain.new_goal
        def racing_new_goal(*a, **k):
            g = real_new_goal(*a, **k)
            o2.open('ma-home', 't', 'r', ['s'], idem_key='anomaly:forced')
            return g
        with mock.patch.object(self.brain, 'new_goal', side_effect=racing_new_goal):
            r1 = o1.open('ma-home', 't', 'r', ['s'], idem_key='anomaly:forced')
        self.assertTrue(r1['duplicate'])
        with self.brain.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM goals').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM steps').fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT goal_id FROM goal_meta").fetchone()[0], r1['goal_id'])

class Gates(Base):
    def test_kill_switch_stops_actions(self):
        g = self.brain.new_goal('ma-home', 'g', 'r', ['a'])
        self.ex.bind('ma-home', self.steps(g['goal_id'])[0], 'touch', 'has-x')
        (self.brain.db_path.parent / 'KILL').touch()
        self.assertTrue(self.ex.run_once('ma-home')['killed'])
        self.assertFalse((self.ws / 'x').exists())
        d = Daemon(self.brain, 'ma-home', self.ex)
        self.assertTrue(d.tick()['killed'])
        self.assertTrue(any('Not-Aus' in n['text'] for n in d.notices()))
        (self.brain.db_path.parent / 'KILL').unlink()
        self.ex.run_once('ma-home'); self.assertTrue((self.ws / 'x').exists())

    def test_privileged_always_needs_approval(self):
        g = self.brain.new_goal('ma-home', 'g', 'r', ['a'])
        sid = self.steps(g['goal_id'])[0]
        self.assertEqual(self.ex.bind('ma-home', sid, 'reboot', 'ok', by='admin')['state'], 'awaiting_approval')
        self.ex.run_once('ma-home'); self.assertFalse((self.ws / 'REBOOTED').exists())
        self.ex.approve('ma-home', sid); self.ex.run_once('ma-home'); self.assertTrue((self.ws / 'REBOOTED').exists())
        with self.assertRaises(ValueError):
            runner.validate({'actions': {'x': {'argv': ['ls'], 'risk': 'privileged', 'auto': True}}})

    def test_privileged_procedure_waits(self):
        from procedures import Procedures
        p = Procedures(self.brain)
        r = p.instantiate(self.ex, {'id': 1, 'project': 'ma-home',
                                    'steps': json.dumps([{'instruction': 'r', 'action': 'reboot', 'check': 'ok'}])},
                          'a1', 'sensor:x', 'down')
        with self.brain.connection() as db:
            self.assertEqual(db.execute('SELECT state FROM exec_bindings').fetchone()[0], 'awaiting_approval')
            self.assertEqual(db.execute('SELECT risk FROM goal_meta WHERE goal_id=?', (r['goal_id'],)).fetchone()[0],
                             'privileged')

    def test_deadline_and_cancel(self):
        o = self.ex.orders
        g = o.open('ma-home', 'g', 'r', ['a'], idem_key='key-1', deadline=int(time.time()) - 1)
        self.ex.bind('ma-home', self.steps(g['goal_id'])[0], 'touch', 'has-x')
        r = self.ex.run_once('ma-home')
        self.assertEqual(r['expired'], [g['goal_id']]); self.assertFalse((self.ws / 'x').exists())
        g2 = o.open('ma-home', 'g', 'r', ['a'], idem_key='key-2')
        self.ex.bind('ma-home', self.steps(g2['goal_id'])[0], 'touch', 'has-x')
        o.cancel(g2['goal_id'])
        self.ex.run_once('ma-home'); self.assertFalse((self.ws / 'x').exists())

    def test_claude_budget_per_order(self):
        from autonomy import validated
        auto = validated({'enabled': True, 'allowed_workspaces': [str(self.ws)], 'db_path': str(self.dir / 'q.db'),
                          'minimum_gap_seconds': 0, 'allowed_templates': ['diagnosis']}, self.dir / 'a.json')
        ex = Executive(self.brain, json.loads(json.dumps(self.acts)), self.ws, auto)
        g = ex.orders.open('ma-home', 'g', 'r', ['a', 'b'], idem_key='key-b', claude_budget=1, topic='.brain/p.md')
        s1, s2 = self.steps(g['goal_id'])
        ex.bind('ma-home', s1, 'diagnose', 'ok'); ex.bind('ma-home', s2, 'diagnose', 'ok')
        r = ex.run_once('ma-home'); self.assertEqual(r['executed'][0]['state'], 'waiting')
        from autonomy import Queue
        q = Queue(auto['db_path']); j = q.claim(auto)
        self.assertEqual(j['topic'], '.brain/p.md')
        q.finish(j['id'], True, 0, 1, 'x')
        r = ex.run_once('ma-home')          # step 1 verified, step 2 would need a second Claude call
        self.assertEqual(r['waiting'][0]['state'], 'done')
        self.assertEqual(r['executed'][0]['reason'], 'claude budget exhausted')
        with q.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0], 1)


class DiagnosisPacket(Base):
    def test_packet_with_log_digest_reaches_claude_job(self):
        from autonomy import validated, Queue, command
        auto = validated({'enabled': True, 'allowed_workspaces': [str(self.ws)], 'db_path': str(self.dir / 'q.db'),
                          'minimum_gap_seconds': 0, 'allowed_templates': ['diagnosis'], 'claude_binary': PY},
                         self.dir / 'a.json')
        self.ex.autonomy = auto
        log = self.dir / 'web.log'
        log.write_text('\n'.join([f'2026-10-14T02:0{i % 10}:00Z info request {i} ok' for i in range(3000)] +
                                 ['2026-10-14T02:11:00Z ERROR bind() to 0.0.0.0:8080 failed (98: Address in use) token=abc123'] * 40 +
                                 ['2026-10-14T02:12:00Z WARN upstream timed out after 30 s']))
        state = {'v': 'active'}
        sensors = {'project': 'ma-home', 'sensors': [{'id': 'web', 'type': 'systemd', 'unit': 'web.service',
                                                      'severity': 5, 'logs': [str(log)]}]}
        d = Daemon(self.brain, 'ma-home', self.ex, sensors_cfg=sensors, autonomy_cfg=auto,
                   opts={'sensor_interval_seconds': 0, 'diagnosis': {'action': 'diagnose', 'check': 'ok'}},
                   sensor_runner=lambda argv, timeout=10: (0, state['v']))
        d.tick(); state['v'] = 'failed'
        r = d.tick(); r2 = d.tick()
        self.assertEqual(r['attention'][0]['decision'], 'diagnosis')
        packet = next((self.ws / '.brain').glob('diagnosis-*.md'))
        text = packet.read_text()
        self.assertEqual(stat.S_IMODE(packet.stat().st_mode), 0o600)
        self.assertIn('×40', text); self.assertIn('Address in use', text); self.assertNotIn('abc123', text)
        self.assertLess(len(text), 3000)
        q = Queue(auto['db_path'])
        with q.connect() as c:
            jobs = [dict(x) for x in c.execute('SELECT * FROM jobs')]
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['topic'], f".brain/{packet.name}")
        prompt = command(auto, jobs[0])[2]
        self.assertIn('Topic: .brain/', prompt); self.assertIn('Read it FIRST', prompt)
        d.tick()
        self.assertEqual(d.proc.listing(), [])  # V10.1: a diagnosis never becomes a repair procedure
        self.assertTrue(r2)


class LogDigest(unittest.TestCase):
    def test_reduction_normalisation_redaction(self):
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / 'a.log'
            f.write_text('\n'.join(['Oct 14 02:00:01 host app[123]: connect to 10.0.0.5:5432 failed: refused'] * 500 +
                                   ['Oct 14 02:00:02 host app[124]: FATAL out of memory password=hunter2'] +
                                   ['info fine'] * 5000))
            r = digest([f])
            self.assertEqual(r['groups'], 2); self.assertEqual(r['lines_read'], 5501)
            self.assertTrue(r['markdown'].startswith('- **fatal**'))
            self.assertIn('×500', r['markdown']); self.assertNotIn('hunter2', r['markdown'])
            self.assertLess(r['chars'], 600)


class Process(unittest.TestCase):
    def test_double_start_refused_and_sigterm_clean(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t); (t / 'ws').mkdir()
            (t / 'brain.json').write_text(json.dumps({'identity': 'person-a', 'allowed_projects': ['ma-home'],
                                                      'state_db': str(t / 'st' / 'b.db')}))
            (t / 'actions.json').write_text('{"actions": {"ok": {"argv": ["true"]}}}')
            (t / 'd.json').write_text(json.dumps({'brain_config': 'brain.json', 'actions': 'actions.json',
                                                  'workspace': 'ws', 'project': 'ma-home', 'tick_seconds': 1}))
            for f in t.glob('*.json'): os.chmod(f, 0o600)
            cmd = [PY, str(ROOT / 'daemon.py'), '--config', str(t / 'd.json'), 'run']
            a = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(2.5)
            b = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self.assertEqual(b.returncode, 3); self.assertIn('already running', b.stderr)
            a.send_signal(signal.SIGTERM)
            self.assertEqual(a.wait(timeout=20), 0)
            a.stdout.close(); a.stderr.close()
            st = subprocess.run([PY, str(ROOT / 'daemon.py'), '--config', str(t / 'd.json'), 'self'],
                                capture_output=True, text=True, timeout=30)
            self.assertEqual(json.loads(st.stdout)['health']['daemon_errors'], 0)


if __name__ == '__main__':
    unittest.main()
