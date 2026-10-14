"""V10: event-driven daemon, procedural memory, self-model, doctor, metrics. Offline, no Claude."""
import json
import os
import sys
import tempfile
import time
import unittest
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain_core import Brain
from executive import Executive
from daemon import Daemon
from procedures import Procedures
import selfmodel

PY = sys.executable


class World(unittest.TestCase):
    """A 'web' service whose state lives in ws/web.state; a sensor reads it through a fake runner."""
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.dir = Path(t.name); self.ws = self.dir / 'ws'; self.ws.mkdir()
        self.state('active')
        self.brain = Brain(self.dir / 'state' / 'b.db', 'person-a', {'ma-home'})
        self.actions = {'actions': {
            'restart-web': {'argv': [PY, '-c', "open('web.state','w').write(open('fix.mode').read() if __import__('os').path.exists('fix.mode') else 'active')"],
                            'idempotent': True},
            'web-ok': {'argv': [PY, '-c', "import sys;sys.exit(0 if open('web.state').read()=='active' else 1)"]},
            'diagnose': {'claude_template': 'repo_audit'},
            'ok': {'argv': [PY, '-c', 'pass']}},
            'limits': {'max_steps_per_run': 3, 'max_local_runs_per_day': 200, 'max_attempts': 1}}
        self.ex = Executive(self.brain, self.actions, self.ws)
        self.sensors = {'project': 'ma-home', 'sensors': [{'id': 'web', 'type': 'systemd', 'unit': 'web.service', 'severity': 4}]}
        self.now = int(datetime(2026, 10, 14, 12, 0).timestamp())

    def state(self, s):
        (self.ws / 'web.state').write_text(s)

    def runner(self, argv, timeout=10):
        return 0, (self.ws / 'web.state').read_text()

    def daemon(self, **opts):
        return Daemon(self.brain, 'ma-home', self.ex, sensors_cfg=json.loads(json.dumps(self.sensors)),
                      opts={'sensor_interval_seconds': 0, **opts}, sensor_runner=self.runner, **self.extra())

    def extra(self):
        return {}

    def tick(self, d, minutes=1):
        self.now += 60 * minutes
        return d.tick(self.now)

    def texts(self, d):
        return [n['text'] for n in d.notices(unread_only=False, limit=50)]


class ProceduralLearning(World):
    def test_learn_confirm_reuse_without_claude(self):
        d = self.daemon()
        self.tick(d)
        self.state('failed'); r = self.tick(d)
        self.assertEqual(r['attention'][0]['decision'], 'human')                 # unknown deviation -> human
        # a human solves it once, via allowlisted actions, and links it to the deviation
        g = self.brain.new_goal('ma-home', 'Web reparieren', 'web aktiv', ['Dienst neu starten'], 1)
        with self.brain.connection() as db:
            sid = db.execute('SELECT id FROM steps WHERE goal_id=?', (g['goal_id'],)).fetchone()[0]
            aid = db.execute("SELECT id FROM cognitive_anomalies WHERE status='open'").fetchone()[0]
        d.proc.link(g['goal_id'], aid, 'sensor:web', 'failed', 'manual')
        self.ex.bind('ma-home', sid, 'restart-web', 'web-ok')
        r = self.tick(d)                                                         # fix runs and verifies
        self.assertEqual(r['learning']['learned'], [])                           # V10.1: not before the cure is seen
        r = self.tick(d)                                                         # sensor sees recovery -> learn
        self.assertEqual(r['learning']['learned'][0]['trigger'], 'sensor:web=failed')
        pid = r['learning']['learned'][0]['procedure']
        self.assertEqual(self.ex.loop.health('ma-home')['active_anomalies'], 0)
        self.state('failed'); r = self.tick(d)
        self.assertEqual(r['attention'][0]['decision'], 'human')                 # proposed != confirmed
        d.proc.set_status(pid, 'confirmed')
        r = self.tick(d)                                     # the still-open deviation is now known
        self.assertEqual(r['attention'][0]['decision'], 'procedure')
        self.assertEqual((self.ws / 'web.state').read_text(), 'active')          # fixed in the same tick
        self.assertEqual(r['claude_calls_started'], 0)
        p = [x for x in d.proc.listing() if x['id'] == pid][0]
        self.assertEqual((p['uses'], p['successes']), (1, 1))
        self.tick(d); self.state('failed'); r = self.tick(d)  # a later, new failure: handled locally again
        self.assertEqual(r['attention'][0]['decision'], 'procedure')
        self.assertEqual([x for x in d.proc.listing() if x['id'] == pid][0]['successes'], 2)
        self.assertTrue(any('Ablauf #' in t and 'gestartet' in t for t in self.texts(d)))

    def test_failing_procedure_is_suspended(self):
        d = self.daemon()
        steps = json.dumps([{'instruction': 'neu starten', 'action': 'restart-web', 'check': 'web-ok'}])
        with self.brain.connection(True) as db:
            db.execute("INSERT INTO procedures(owner,project,name,trigger_subject,trigger_state,steps,status,created) "
                       "VALUES('person-a','ma-home','x','sensor:web','failed',?,'confirmed',0)", (steps,))
        (self.ws / 'fix.mode').write_text('failed')                               # the fix no longer works
        self.tick(d)
        for _ in range(3):
            self.state('active'); self.tick(d)
            self.state('failed'); self.tick(d); self.tick(d)
        p = d.proc.listing()[0]
        self.assertEqual(p['status'], 'suspended'); self.assertGreaterEqual(p['failures'], 3)
        self.state('active'); self.tick(d); self.state('failed')
        self.assertEqual(self.tick(d)['attention'][0]['decision'], 'human')

    def test_one_goal_per_open_deviation(self):
        d = self.daemon()
        with self.brain.connection(True) as db:
            db.execute("INSERT INTO procedures(owner,project,name,trigger_subject,trigger_state,steps,status,created) "
                       "VALUES('person-a','ma-home','x','sensor:web','failed',?,'confirmed',0)",
                       (json.dumps([{'instruction': 'a', 'action': 'ok', 'check': 'web-ok'}]),))
        self.tick(d); self.state('failed')
        self.tick(d); self.tick(d); self.tick(d)
        with self.brain.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM goal_links').fetchone()[0], 1)


class GuardRails(World):
    def test_fix_that_does_not_cure_is_not_learned(self):
        d = self.daemon(); self.tick(d); self.state('failed'); self.tick(d)
        g = self.brain.new_goal('ma-home', 'x', 'y', ['harmlos'], 1)
        with self.brain.connection() as db:
            sid = db.execute('SELECT id FROM steps WHERE goal_id=?', (g['goal_id'],)).fetchone()[0]
            aid = db.execute("SELECT id FROM cognitive_anomalies WHERE status='open'").fetchone()[0]
        d.proc.link(g['goal_id'], aid, 'sensor:web', 'failed', 'manual')
        self.ex.bind('ma-home', sid, 'ok', 'ok')            # "succeeds" but the service stays failed
        for _ in range(3):
            self.tick(d)
        self.assertEqual(d.proc.listing(), [])

    def test_failed_manual_fix_is_not_learned(self):
        d = self.daemon(); self.tick(d); self.state('failed'); self.tick(d)
        (self.ws / 'fix.mode').write_text('failed')
        g = self.brain.new_goal('ma-home', 'x', 'y', ['neu starten'], 1)
        with self.brain.connection() as db:
            sid = db.execute('SELECT id FROM steps WHERE goal_id=?', (g['goal_id'],)).fetchone()[0]
            aid = db.execute("SELECT id FROM cognitive_anomalies WHERE status='open'").fetchone()[0]
        d.proc.link(g['goal_id'], aid, 'sensor:web', 'failed', 'manual')
        self.ex.bind('ma-home', sid, 'restart-web', 'web-ok')
        r = self.tick(d)
        self.assertEqual(r['learning']['learned'], [])
        self.assertEqual(d.proc.listing(), [])

    def test_running_goal_blocks_second_goal_for_same_subject(self):
        acts = json.loads(json.dumps(self.actions)); acts['limits']['max_attempts'] = 3
        self.ex = Executive(self.brain, acts, self.ws)
        d = self.daemon()
        with self.brain.connection(True) as db:
            db.execute("INSERT INTO procedures(owner,project,name,trigger_subject,trigger_state,steps,status,created) "
                       "VALUES('person-a','ma-home','x','sensor:web','*',?,'confirmed',0)",
                       (json.dumps([{'instruction': 'a', 'action': 'ok', 'check': 'web-ok'}]),))
        self.tick(d); self.state('failed')
        self.assertEqual(self.tick(d)['attention'][0]['decision'], 'procedure')  # check fails, will retry
        self.state('crashed')
        self.assertEqual(self.tick(d)['attention'][0]['decision'], 'already handled')

    def test_diagnosis_needs_enabled_claude_route(self):
        d = self.daemon(diagnosis={'action': 'diagnose', 'check': 'ok', 'min_severity': 4})
        self.tick(d); self.state('failed')
        self.assertEqual(self.tick(d)['attention'][0]['decision'], 'human')

    def test_no_sleep_in_conserve_mode(self):
        d = self.daemon(sleep_hour=3, homeostasis={'min_disk_percent': 101})
        self.now = int(datetime(2026, 10, 15, 3, 1).timestamp())
        self.assertNotIn('sleep', d.tick(self.now))


class DiagnosisAndJobs(World):
    def extra(self):
        from autonomy import validated
        self.auto = validated({'enabled': True, 'allowed_workspaces': [str(self.ws)], 'db_path': str(self.dir / 'q.db'),
                               'minimum_gap_seconds': 0, 'allowed_templates': ['repo_audit', 'extension_research']},
                              self.dir / 'a.json')
        self.ex.autonomy = self.auto
        return {'autonomy_cfg': self.auto}

    def test_unknown_severe_deviation_queues_one_budgeted_diagnosis(self):
        from autonomy import Queue
        d = self.daemon(diagnosis={'action': 'diagnose', 'check': 'ok', 'min_severity': 4})
        self.tick(d); self.state('failed')
        r = self.tick(d)
        self.assertEqual(r['attention'][0]['decision'], 'diagnosis')
        self.tick(d); self.tick(d)
        q = Queue(self.auto['db_path'])
        with q.connect() as c:
            jobs = c.execute('SELECT id,template,status FROM jobs').fetchall()
        self.assertEqual([(j['template'], j['status']) for j in jobs], [('repo_audit', 'queued')])  # once, not per tick
        job = q.claim(self.auto); q.finish(job['id'], True, 0, 5, 'Ursache: Port 8080 belegt.')
        r = self.tick(d)
        self.assertEqual(r['harvested'], 1)
        with self.brain.connection() as db:
            m = db.execute("SELECT status,kind,source FROM memory").fetchone()
        self.assertEqual((m['status'], m['kind']), ('proposed', 'hypothesis'))     # never a confirmed fact
        self.assertEqual(self.tick(d)['harvested'], 0)

    def test_stale_second_daemon_cannot_duplicate_diagnosis(self):
        from autonomy import Queue
        diag = {'action': 'diagnose', 'check': 'ok', 'min_severity': 4}
        d1, d2 = self.daemon(diagnosis=diag), self.daemon(diagnosis=diag)
        self.tick(d1); self.state('failed'); r1 = self.tick(d1)
        self.assertEqual(r1['attention'][0]['decision'], 'diagnosis')
        with self.brain.connection(True) as db:     # d2 read the state before d1 saved its cursor
            db.execute('UPDATE daemon_state SET last_anomaly_seen=0')
        r2 = self.tick(d2)
        self.assertEqual(r2['attention'][0]['decision'], 'already handled')
        with Queue(self.auto['db_path']).connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0], 1)
        with self.brain.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM goals').fetchone()[0], 1)

    def test_resolved_after_diagnosis_is_not_learned(self):
        from autonomy import Queue
        d = self.daemon(diagnosis={'action': 'diagnose', 'check': 'ok', 'min_severity': 4})
        self.tick(d); self.state('failed'); self.tick(d); self.tick(d)
        q = Queue(self.auto['db_path']); j = q.claim(self.auto); q.finish(j['id'], True, 0, 1, 'Ursache X')
        self.tick(d)                                   # diagnosis step verified
        self.state('active'); self.tick(d); self.tick(d)  # the symptom disappears (for whatever reason)
        self.assertEqual(d.proc.listing(), [])

    def test_sleep_rollup_research_and_pruning(self):
        from autonomy import Queue
        d = self.daemon(sleep_hour=3, research={'enabled': True, 'min_failures': 3})
        g = self.brain.new_goal('ma-home', 'x', 'y', ['a', 'b', 'c'])
        for i in range(3):
            self.brain.episode('ma-home', 'action:restart-web', 's', 'failure', 'e')
        with self.brain.connection(True) as db:
            db.execute('UPDATE episodes SET verified=1')
            db.execute("INSERT INTO exec_runs(owner,step_id,kind,action,started) VALUES('person-a','s','action','ok',1)")
        self.now = int(datetime(2026, 10, 15, 2, 58).timestamp())
        self.assertNotIn('sleep', self.tick(d))
        r = self.tick(d, minutes=3)                                              # 03:01 local
        self.assertIn('sleep', r)
        self.assertEqual(r['sleep']['research_queued'], 'failing action restart-web')
        self.assertEqual(r['sleep']['metrics']['day'], '2026-10-14')
        self.assertEqual(r['sleep']['pruned_runs'], 1)
        self.assertNotIn('sleep', self.tick(d))                                  # once per day
        with Queue(self.auto['db_path']).connect() as c:
            self.assertEqual(c.execute("SELECT topic FROM jobs").fetchone()[0], 'failing action restart-web')
        self.assertTrue(any('Wiederkehrender bestätigter Fehler' in t for t in self.texts(d)))
        self.assertEqual(selfmodel.history(self.brain, 3650)[0]['day'], '2026-10-14')
        self.assertTrue(g)


class Regulation(World):
    def test_outage_conserve_and_pause(self):
        d = self.daemon(); self.tick(d)
        d2 = self.daemon()
        r = self.tick(d2, minutes=45)
        self.assertGreater(r['outage_s'], 2000)
        self.assertTrue(any('nicht aktiv' in t for t in self.texts(d2)))
        d3 = self.daemon(homeostasis={'min_disk_percent': 101})
        r = self.tick(d3)
        self.assertEqual(r['mode'], 'conserve'); self.assertEqual(self.ex.limits['max_steps_per_run'], 3)
        self.assertTrue(any('Sparbetrieb' in t for t in self.texts(d3)))
        d3.loop.set_paused('ma-home', True)
        self.assertTrue(self.tick(d3)['paused'])

    def test_bad_diagnosis_config_rejected(self):
        with self.assertRaises(ValueError):
            self.daemon(diagnosis={'action': 'rm-everything', 'check': 'ok'})


class SelfModelAndDoctor(World):
    def test_snapshot_knows_known_and_unknown(self):
        d = self.daemon(); self.tick(d); self.state('failed'); self.tick(d)
        snap = selfmodel.snapshot(self.brain, 'ma-home', self.ex, d.proc, self.sensors)
        self.assertEqual(snap['open_deviations'][0]['decision'], 'unknown: needs human review')
        self.assertEqual(snap['capabilities']['sensors'], ['web'])
        self.assertIn('restart-web', snap['capabilities']['actions'])
        self.assertIsNotNone(snap['health']['heartbeat_age_s'])
        with self.brain.connection(True) as db:
            db.execute("INSERT INTO procedures(owner,project,name,trigger_subject,trigger_state,steps,status,created) "
                       "VALUES('person-a','ma-home','x','sensor:web','failed','[]','confirmed',0)")
        snap = selfmodel.snapshot(self.brain, 'ma-home', self.ex, d.proc)
        self.assertTrue(snap['open_deviations'][0]['decision'].startswith('known: procedure #'))

    @unittest.skipIf(os.name != 'posix', 'posix permissions')
    def test_new_brain_db_is_owner_only(self):
        import stat
        b = Brain(self.dir / 'fresh' / 'n.db', 'person-a', {'ma-home'})
        self.assertEqual(stat.S_IMODE(b.db_path.stat().st_mode), 0o600)
        self.assertEqual([f for f in selfmodel.doctor(b)['findings'] if f['check'] == 'permissions'], [])

    def test_doctor_permissions_and_identity(self):
        os.chmod(self.brain.db_path, 0o644)
        cfg = self.dir / 'c.json'; cfg.write_text('{}'); os.chmod(cfg, 0o666)
        r = selfmodel.doctor(self.brain, [cfg])
        self.assertFalse(r['ok'])
        self.assertEqual({f['check'] for f in r['findings'] if f['level'] == 'error'} & {'permissions'}, {'permissions'})
        os.chmod(self.brain.db_path, 0o600); os.chmod(cfg, 0o600)
        Brain(self.brain.db_path, 'person-b', {'ma-home'}).propose('ma-home', 't', 'c', 's')
        self.assertEqual([f['level'] for f in selfmodel.doctor(self.brain)['findings'] if f['check'] == 'identity isolation'], ['warning'])
        self.assertFalse(selfmodel.doctor(self.brain, strict_identity=True)['ok'])

    def test_strict_identity_mcp_refuses_shared_db(self):
        from mcp_server_v5 import Server
        Brain(self.brain.db_path, 'person-b', {'ma-home'}).propose('ma-home', 't', 'c', 's')
        with self.assertRaises(ValueError):
            Server({'identity': 'person-a', 'allowed_projects': ['ma-home'], 'state_db': str(self.brain.db_path),
                    'strict_identity': True})

    def test_brain_self_tool(self):
        from mcp_server_v5 import Server
        acts = self.dir / 'acts.json'; acts.write_text(json.dumps(self.actions)); os.chmod(acts, 0o600)
        d = self.daemon(); self.tick(d); self.state('failed'); self.tick(d)
        s = Server({'identity': 'person-a', 'allowed_projects': ['ma-home'], 'state_db': str(self.brain.db_path),
                    'actions': str(acts), 'workspace': str(self.ws)})
        r = json.loads(s.call('brain_self', {'project': 'ma-home'})['content'][0]['text'])
        self.assertEqual(r['open_deviations'][0]['subject'], 'sensor:web')
        self.assertTrue(r['unread_notices'])
        self.assertEqual(r['claude_calls_by_this_snapshot'], 0)


if __name__ == '__main__':
    unittest.main()
