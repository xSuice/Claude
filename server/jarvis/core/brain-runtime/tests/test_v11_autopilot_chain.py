"""V11 phase D/E: performance autopilot (pinned allowlist, before/after, rollback, revert) and the
end-to-end order chain (local only / helper / Claude escalation / no network). Offline; helpers
are a fake provider on 127.0.0.1."""
import hashlib
import json
import os
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'tests'))
from brain_core import Brain
from executive import Executive
from daemon import Daemon
from performance_intelligence import PerfIntel, Collector
from perf_autopilot import Autopilot, load_allowlist
from provider_adapter import HelperClient
from route_policy import RoutePolicy
import test_v11_providers as tp

PY = sys.executable


class AutopilotTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); self.d = Path(t.name); (self.d / 'ws').mkdir()
        self.b = Brain(self.d / 'b.db', 'person-a', {'ma-home'})
        self.ex = Executive(self.b, {'actions': {'ok': {'argv': [PY, '-c', 'pass']}}}, self.d / 'ws')
        empty = self.d / 'empty'; empty.mkdir()
        self.perf = PerfIntel(self.d / 'perf.db', Collector(empty / 'p', empty / 's', disk_paths=[]))
        self.dmn = Daemon(self.b, 'ma-home', self.ex, opts={'sensor_interval_seconds': 300}, perf=self.perf)
        self.allow = {'measures': {'slow_sensors': {'targets': ['self_load'], 'metric': 'self_cpu_pct', 'min_gain': 0.2, 'auto': True}}}
        self.now = 10_000

    def feed(self, value, n=5, cond_active=True):
        with self.perf._conn() as c:
            for i in range(n):
                self.now += 60
                c.execute('INSERT OR REPLACE INTO perf_raw VALUES(?,?)', (self.now, json.dumps({'self_cpu_pct': value})))
            c.execute('INSERT OR REPLACE INTO perf_state VALUES(?,?,?,?,?)', ('self_load', int(cond_active), 0, 0, None))

    def ap(self, autorun=True, **kw):
        return Autopilot(self.dmn, self.allow, autorun=autorun, window=5, **kw)

    def test_pinned_allowlist(self):
        f = self.d / 'allow.json'; f.write_text(json.dumps(self.allow)); os.chmod(f, 0o600)
        good = hashlib.sha256(f.read_bytes()).hexdigest()
        self.assertIn('slow_sensors', load_allowlist(f, good)['measures'])
        with self.assertRaises(PermissionError):
            load_allowlist(f, '0' * 64)
        f.write_text(json.dumps({'measures': {'restart_docker': {}}})); os.chmod(f, 0o600)
        with self.assertRaises(ValueError):
            load_allowlist(f, hashlib.sha256(f.read_bytes()).hexdigest())
        os.chmod(f, 0o666)
        with self.assertRaises(PermissionError):
            load_allowlist(f, hashlib.sha256(f.read_bytes()).hexdigest())

    def test_without_autorun_only_a_proposal(self):
        self.feed(30.0)
        r = self.ap(autorun=False).step(self.now)
        self.assertEqual(r['state'], 'awaiting_approval'); self.assertEqual(self.dmn.o['sensor_interval_seconds'], 300)
        self.assertTrue(any('Autopilot schlägt slow_sensors vor' in n['text'] for n in self.dmn.notices()))

    def test_retain_on_measured_gain_and_learn(self):
        ap = self.ap(); self.feed(30.0)
        self.assertEqual(ap.step(self.now)['state'], 'measuring_after')
        self.assertEqual(self.dmn.o['sensor_interval_seconds'], 600)
        self.feed(12.0)
        r = ap.step(self.now)
        self.assertEqual(r['state'], 'retained'); self.assertAlmostEqual(r['gain'], 0.6)
        with self.b.connection() as db:
            e = db.execute("SELECT outcome, verified FROM episodes WHERE task_type='perf:slow_sensors'").fetchone()
        self.assertEqual(tuple(e), ('success', 1))

    def test_rollback_without_gain_and_cooldown(self):
        ap = self.ap(); self.feed(30.0); ap.step(self.now)
        self.feed(29.0)
        self.assertEqual(ap.step(self.now)['state'], 'rolled_back')
        self.assertEqual(self.dmn.o['sensor_interval_seconds'], 300)
        self.feed(30.0)
        self.assertEqual(ap.step(self.now)['state'], 'idle')       # cooldown: no immediate retry loop

    def test_rollback_on_quality_regression(self):
        ap = self.ap(); self.feed(30.0); ap.step(self.now)
        with self.b.connection(True) as db:
            db.execute("INSERT INTO cognitive_anomalies(id,owner,project,event_id,expectation_id,created) VALUES('x','person-a','ma-home','e','f',1)")
        self.feed(5.0)
        r = ap.step(self.now)
        self.assertEqual(r['state'], 'rolled_back'); self.assertEqual(self.dmn.o['sensor_interval_seconds'], 300)
        self.assertIn('quality regression', ap.history()[0]['outcome'])

    def test_retained_measure_reverts_when_condition_clear(self):
        ap = self.ap(revert_after_h=1); self.feed(30.0); ap.step(self.now); self.feed(10.0); ap.step(self.now)
        self.feed(5.0, cond_active=False); ap.step(self.now)
        self.now += 3700
        self.assertEqual(ap.step(self.now)['state'], 'reverted'); self.assertEqual(self.dmn.o['sensor_interval_seconds'], 300)

    def test_daily_cap(self):
        ap = self.ap(max_runs_per_day=1); self.feed(30.0); ap.step(self.now); self.feed(29.0); ap.step(self.now)
        self.feed(30.0); self.now += 7 * 3600
        self.assertEqual(ap.step(self.now)['reason'], 'daily cap')


class ChainBase(tp.Base):
    def world(self, helper=True, autonomy=False, trusted=True, cloud=True):
        ws = self.d / 'ws'; ws.mkdir()
        (ws / 'web.state').write_text('active')
        self.b = Brain(self.d / 'b.db', 'person-a', {'ma-home'})
        acts = {'actions': {'restart': {'argv': [PY, '-c', "open('web.state','w').write('active')"], 'idempotent': True},
                            'web-ok': {'argv': [PY, '-c', "import sys;sys.exit(0 if open('web.state').read()=='active' else 1)"]},
                            'packet-ok': {'argv': [PY, '-c', "import glob,sys;sys.exit(0 if glob.glob('.brain/diagnosis-*.md') else 1)"]},
                            'hint': {'helper_task': 'diagnose_hint', 'fallback_template': 'diagnosis'},
                            'diagnose': {'claude_template': 'diagnosis'}}}
        cfg = json.loads(json.dumps(self.cfg)); cfg['cloud_enabled'] = cloud
        h = self.client(cfg)
        route = RoutePolicy(self.d / 'r.db', [PY, '-c', 'import json;print(json.dumps({"target":"helper:fake"}))'], h,
                            mode='active', provider_order=['fake', 'fake2'])
        if trusted:
            route._reliable = lambda p, t: (True, 'test')
        self.auto = None
        if autonomy:
            from autonomy import validated
            self.auto = validated({'enabled': True, 'allowed_workspaces': [str(ws)], 'db_path': str(self.d / 'q.db'),
                                   'minimum_gap_seconds': 0, 'allowed_templates': ['diagnosis']}, self.d / 'a.json')
        ex = Executive(self.b, acts, ws, self.auto, helpers=h, route=route)
        self.st = {'v': 'active'}
        d = Daemon(self.b, 'ma-home', ex, autonomy_cfg=self.auto, sensor_runner=lambda a, timeout=10: (0, (ws / 'web.state').read_text()),
                   sensors_cfg={'project': 'ma-home', 'sensors': [{'id': 'web', 'type': 'systemd', 'unit': 'web.service', 'severity': 5}]},
                   opts={'sensor_interval_seconds': 0, 'diagnosis': {'action': 'hint' if helper else 'diagnose', 'check': 'packet-ok'}})
        self.ws, self.ex = ws, ex
        return d

    def calls(self):
        with self.ex.helpers._conn() as c:
            return c.execute("SELECT provider, status FROM helper_calls").fetchall()

    def jobs(self):
        if not self.auto:
            return 0
        from autonomy import Queue
        with Queue(self.auto['db_path']).connect() as c:
            return c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]


class Chain(ChainBase):
    def test_known_failure_fixed_locally_without_any_model(self):
        d = self.world(autonomy=True)
        with self.b.connection(True) as db:
            db.execute("INSERT INTO procedures(owner,project,name,trigger_subject,trigger_state,steps,status,created) VALUES"
                       "('person-a','ma-home','x','sensor:web','failed',?,'confirmed',0)",
                       (json.dumps([{'instruction': 'neu starten', 'action': 'restart', 'check': 'web-ok'}]),))
        d.tick(); (self.ws / 'web.state').write_text('failed')
        r = d.tick()
        self.assertEqual(r['attention'][0]['decision'], 'procedure')
        self.assertEqual((self.ws / 'web.state').read_text(), 'active')
        self.assertEqual((self.calls(), self.jobs(), Fake_hits()), ([], 0, 0))

    def test_unknown_failure_uses_permitted_helper(self):
        tp.Fake.mode = 'grounded'   # V11.1: the answer must cite the diagnosis packet verbatim
        d = self.world()
        d.tick(); (self.ws / 'web.state').write_text('failed'); d.tick(); r = d.tick()
        self.assertEqual([tuple(x) for x in self.calls()], [('fake', 'ok')])
        with self.b.connection() as db:
            self.assertEqual(db.execute("SELECT status FROM steps").fetchone()[0], 'verified')
            self.assertEqual(db.execute("SELECT status, kind FROM memory").fetchone()[:], ('proposed', 'hypothesis'))
        self.assertEqual(d._state()['errors'], 0)

    def test_helper_outage_escalates_to_claude_queue(self):
        tp.Fake.mode = '500'
        d = self.world(autonomy=True)
        d.tick(); (self.ws / 'web.state').write_text('failed'); d.tick(); d.tick()
        # default helper budget 1: one failed helper call, then straight to the bounded Claude queue
        self.assertEqual([x[1] for x in self.calls()], ['http_error'])
        self.assertEqual(self.jobs(), 1)

    def test_helper_failover_within_budget(self):
        tp.Fake.mode = '500'
        d = self.world(autonomy=True); d.o['diagnosis']['helper_budget'] = 2
        d.tick(); (self.ws / 'web.state').write_text('failed'); d.tick(); d.tick()
        self.assertEqual(sorted(x[0] for x in self.calls()), ['fake', 'fake2'])
        self.assertEqual(self.jobs(), 1)

    def test_no_network_and_no_budget_stays_stable(self):
        d = self.world(cloud=False)
        d.tick(); (self.ws / 'web.state').write_text('failed')
        for _ in range(4):
            d.tick()
        with self.b.connection() as db:
            self.assertIn('parked', db.execute("SELECT outcome FROM steps").fetchone()[0])
        self.assertEqual(d._state()['errors'], 0); self.assertEqual(tp.Fake.hits, 0)

    def test_conserve_mode_defers_helpers(self):
        d = self.world()
        d.o['homeostasis'] = {'min_disk_percent': 101}
        d.tick(); (self.ws / 'web.state').write_text('failed'); d.tick(); r = d.tick()
        self.assertEqual(tp.Fake.hits, 0)
        with self.b.connection() as db:
            self.assertEqual(db.execute("SELECT state FROM exec_bindings").fetchone()[0], 'ready')


def Fake_hits():
    return tp.Fake.hits


if __name__ == '__main__':
    unittest.main()
