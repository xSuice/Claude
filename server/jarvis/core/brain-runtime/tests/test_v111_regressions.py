"""V11.1 regressions for the independent V11 audit (written first, red on V11, green after the fix).

P0-1 shadow mode must never call a helper, whatever the router says.
P0-2 an existing diagnosis packet is not quality evidence: empty, ungrounded, fabricated or
     injected helper answers never verify a step or raise a helper's success rate.
P1-3 daily token budget enforced (per identity+project, global cap), reserved before sending,
     race-free across processes/threads and across restarts.
P1-4 explicit, separately enabled canary runs on public test cases build trust; never via shadow.
Offline: helpers are the fake OpenAI-compatible server on 127.0.0.1."""
import json
import sqlite3
import sys
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'tests'))
from provider_adapter import HelperClient, Refused
from route_policy import RoutePolicy
import test_v11_providers as tp
from test_v11_autopilot_chain import ChainBase

PY = sys.executable


# ---------------------------------------------------------------- P0-1
class ShadowNeverCalls(tp.Base):
    executive = tp.Routing.executive

    def test_router_names_helper_in_shadow_mode_no_call_any_class(self):
        for cls in ('public', 'internal', 'private'):
            with self.subTest(cls=cls):
                r = self.d / 'router.py'
                r.write_text('import sys,json;json.load(sys.stdin);print(json.dumps({"target":"helper:fake"}))')
                rp = RoutePolicy(self.d / f'r-{cls}.db', [PY, str(r)], self.client(), mode='shadow', provider_order=['fake'])
                rp._reliable = lambda p, t: (True, 'even if it were trusted')
                d = rp.decide({'task_type': 'diagnose_hint', 'risk': 'read', 'data_class': cls, 'size_chars': 10,
                               'has_procedure': False, 'fallback': 'claude'}, 'ma-home')
                self.assertFalse(d['executed'].startswith('helper'), d)
                self.assertEqual(d['router']['target'], 'helper:fake')       # recorded as hypothetical only

    def test_shadow_execution_path_makes_zero_requests(self):
        ex, b, route = self.executive('shadow', {'target': 'helper:fake', 'reason': 'router likes it'}, autonomy=True)
        route._reliable = lambda p, t: (True, 'trusted')
        r = ex.run_once('ma-home')
        self.assertEqual(tp.Fake.hits, 0)
        self.assertEqual(r['executed'][0]['state'], 'waiting')               # V10.1 path: bounded Claude queue

    def test_shadow_without_router_zero_requests(self):
        ex, _, route = self.executive('shadow', None)
        route._reliable = lambda p, t: (True, 'trusted')
        ex.run_once('ma-home'); self.assertEqual(tp.Fake.hits, 0)

    def test_unknown_mode_refused(self):
        with self.assertRaises(ValueError):
            RoutePolicy(self.d / 'x.db', None, None, mode='canary')          # canary is not a routing mode


# ---------------------------------------------------------------- P0-2
class HelperQuality(ChainBase):
    def run_chain(self, mode):
        tp.Fake.mode = mode
        d = self.world()
        d.tick(); (self.ws / 'web.state').write_text('failed'); d.tick(); d.tick()
        with self.b.connection() as db:
            step = db.execute('SELECT status FROM steps').fetchone()[0]
            anomaly = db.execute("SELECT status FROM cognitive_anomalies").fetchone()[0]
        s = next((x for x in self.ex.helpers.stats() if x['provider'] == 'fake'), {})
        return step, s.get('verified_ok') or 0, s.get('verified_bad') or 0, anomaly

    def test_injected_answer_never_verified(self):
        step, ok, bad, _ = self.run_chain('inject')
        self.assertNotEqual(step, 'verified'); self.assertEqual(ok, 0); self.assertGreaterEqual(bad, 1)
        with self.ex.helpers._conn() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM helper_calls WHERE suspicious=1 AND verified=1').fetchone()[0], 0)

    def test_empty_ungrounded_and_fabricated_answers_not_verified(self):
        for mode in ('empty', 'ok', 'fabricated'):
            with self.subTest(mode=mode):
                self.reset()
                step, ok, bad, _ = self.run_chain(mode)
                self.assertNotEqual(step, 'verified'); self.assertEqual(ok, 0)

    def test_grounded_answer_verified_but_failure_not_marked_fixed(self):
        step, ok, bad, anomaly = self.run_chain('grounded')
        self.assertEqual((step, ok, bad), ('verified', 1, 0))
        self.assertEqual(anomaly, 'open')                  # a diagnosis is not a repair; only the sensor closes it
        with self.b.connection() as db:
            self.assertEqual(db.execute("SELECT status, kind FROM memory").fetchone()[:], ('proposed', 'hypothesis'))

    def reset(self):
        import shutil
        for p in self.d.iterdir():
            if p.name != 'fake.key':
                shutil.rmtree(p) if p.is_dir() else p.unlink()

    def test_suspicious_answer_can_never_be_marked_ok(self):
        tp.Fake.mode = 'inject'
        h = HelperClient(self.cfg, self.d / 'h2.db', 'person-a', handlers=[tp.urllib.request.ProxyHandler({})])
        r = h.call('fake', 'diagnose_hint', 'x', project='ma-home')
        h.mark_call(r['call_id'], True)                      # even a buggy/forged caller cannot count it
        with h._conn() as c:
            self.assertEqual(c.execute('SELECT verified FROM helper_calls WHERE id=?', (r['call_id'],)).fetchone()[0], 0)

    def test_legacy_wrong_successes_are_corrected_with_audit(self):
        db = self.d / 'h.db'
        HelperClient(self.cfg, db, 'person-a', handlers=[]).stats()
        c = sqlite3.connect(db)
        c.execute("INSERT INTO helper_calls(ts,identity,project,order_id,provider,task_type,data_class,status,suspicious,verified) "
                  "VALUES(1,'person-a','ma-home','g1','fake','diagnose_hint','internal','ok',1,1)")
        c.commit(); c.close()
        h = HelperClient(self.cfg, db, 'person-a', handlers=[])
        with h._conn() as c:
            self.assertEqual(c.execute('SELECT verified FROM helper_calls WHERE order_id=?', ('g1',)).fetchone()[0], 0)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM helper_audit').fetchone()[0], 1)


# ---------------------------------------------------------------- P1-3
class TokenBudget(tp.Base):
    def cfg2(self, **kw):
        c = json.loads(json.dumps(self.cfg)); c.update(kw)
        c['providers']['fake']['limits'] = {'rpm': 1000, 'rpd': 1000, 'tpd': 10_000_000}
        c['daily_call_budget'] = kw.get('daily_call_budget', 1000)
        c['egress']['person-a']['lab'] = {'internal': ['fake']}
        return c

    def test_zero_token_budget_means_zero_requests(self):
        h = self.client(self.cfg2(daily_token_budget=0))
        self.assertIn('token budget', h.eligible('fake', 'diagnose_hint', 'internal', 'ma-home') or '')
        with self.assertRaises(Refused):
            h.call('fake', 'diagnose_hint', 'x', project='ma-home')
        self.assertEqual(tp.Fake.hits, 0)

    def test_reservation_refuses_when_nearly_exhausted(self):
        h = self.client(self.cfg2(daily_token_budget=700))
        with self.assertRaises(Refused):                    # 600 max_tokens + input estimate > 700
            h.call('fake', 'diagnose_hint', 'x' * 400, project='ma-home', max_tokens=600)
        self.assertEqual(tp.Fake.hits, 0)
        h = self.client(self.cfg2(daily_token_budget=900))
        h.call('fake', 'diagnose_hint', 'x' * 400, project='ma-home', max_tokens=600)   # real use 150 tokens
        with self.assertRaises(Refused):
            h.call('fake', 'diagnose_hint', 'x' * 400, project='ma-home', max_tokens=600)
        self.assertEqual(tp.Fake.hits, 1)

    def test_per_project_and_global_cap_survive_restart(self):
        # estimate = ceil((system+prompt chars)/3) + 32 + max_tokens = 52 + max for 'x'; the fake bills 150 per call
        cfg = self.cfg2(daily_token_budget=1100, global_daily_token_budget=1300)
        self.client(cfg).call('fake', 'diagnose_hint', 'x', project='ma-home', max_tokens=600)
        h = self.client(cfg)                                # "restart": new client, same DB
        h.call('fake', 'diagnose_hint', 'x', project='ma-home', max_tokens=800)          # 150 + 852 <= 1100
        with self.assertRaises(Refused) as e:               # 300 + 852 > 1100 (project)
            h.call('fake', 'diagnose_hint', 'x', project='ma-home', max_tokens=800)
        self.assertIn('token budget', str(e.exception))
        h.call('fake', 'diagnose_hint', 'x', project='lab', max_tokens=600)              # own project budget
        with self.assertRaises(Refused) as e:               # global: 450 + 852 > 1300
            h.call('fake', 'diagnose_hint', 'x', project='lab', max_tokens=800)
        self.assertIn('global', str(e.exception))
        self.assertEqual(tp.Fake.hits, 3)

    def test_parallel_requests_never_exceed_call_budget(self):
        tp.Fake.mode = 'slowish'
        cfg = self.cfg2(daily_call_budget=3, daily_token_budget=10_000_000)
        errs = []
        def go():
            try:
                self.client(cfg).call('fake', 'diagnose_hint', 'x', project='ma-home')
            except Refused:
                pass
            except Exception as e:  # noqa: BLE001
                errs.append(e)
        ts = [threading.Thread(target=go) for _ in range(10)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(errs, []); self.assertLessEqual(tp.Fake.hits, 3)


    def test_v11_database_upgrade_is_safe_with_parallel_processes(self):
        import subprocess
        db = self.d / 'old.db'
        c = sqlite3.connect(db)   # exact V11 schema (no reserved_tokens / origin)
        c.executescript('''CREATE TABLE helper_calls(id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, identity TEXT NOT NULL,
            project TEXT NOT NULL, order_id TEXT, provider TEXT NOT NULL, task_type TEXT NOT NULL, data_class TEXT NOT NULL,
            status TEXT NOT NULL, latency_ms INTEGER, in_tokens INTEGER, out_tokens INTEGER, cost_usd REAL, error TEXT,
            suspicious INTEGER NOT NULL DEFAULT 0, verified INTEGER);'''); c.commit(); c.close()
        cfgf = self.d / 'p.json'; cfgf.write_text(json.dumps(self.cfg))
        code = (f"import sys,json;sys.path.insert(0,{str(ROOT)!r});from provider_adapter import HelperClient;"
                f"HelperClient(json.load(open({str(cfgf)!r})),{str(db)!r},'person-a').stats()")
        ps = [subprocess.Popen([PY, '-c', code], stderr=subprocess.PIPE) for _ in range(8)]
        errs = [p.communicate()[1].decode() for p in ps]
        self.assertEqual([e for e in errs if e], [])
        c = sqlite3.connect(db)
        cols = {r[1] for r in c.execute('PRAGMA table_info(helper_calls)')}; c.close()
        self.assertLessEqual({'reserved_tokens', 'origin'}, cols)


# ---------------------------------------------------------------- P1-4
class Canary(tp.Base):
    def suite(self, cases):
        f = self.d / 'canary.json'; f.write_text(json.dumps({'cases': cases})); return f

    CASES = [{'id': f'c{i}', 'task_type': 'diagnose_hint', 'prompt': f'Öffentlicher Testfall {i}: Dienst web ausgefallen, Zustand failed.',
              'verify': {'type': 'grounded'}} for i in range(4)]

    def test_disabled_by_default_no_request(self):
        from canary import run
        with self.assertRaises(PermissionError):
            run(self.client(), self.suite(self.CASES), provider='fake', project='ma-home')
        self.assertEqual(tp.Fake.hits, 0)

    def test_enabled_canary_builds_trust_only_on_public_cases_within_cap(self):
        from canary import run
        cfg = json.loads(json.dumps(self.cfg)); cfg['canary'] = {'enabled': True, 'max_calls_per_run': 3}
        tp.Fake.mode = 'grounded'
        cases = self.CASES + [{'id': 'priv', 'task_type': 'diagnose_hint', 'prompt': 'Mail an max@example.org prüfen',
                               'verify': {'type': 'grounded'}}]
        h = self.client(cfg)
        res = run(h, self.suite(cases[-1:] + cases), provider='fake', project='ma-home')
        self.assertEqual(res['refused'][0]['id'], 'priv')                    # private data never sent
        self.assertEqual(len(res['results']), 3); self.assertEqual(tp.Fake.hits, 3)
        self.assertTrue(all(r['verified'] for r in res['results']))
        with h._conn() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM helper_calls WHERE origin='canary' AND verified=1").fetchone()[0], 3)
        rp = RoutePolicy(self.d / 'r.db', None, h, mode='active', min_samples=3)
        self.assertTrue(rp._reliable('fake', 'diagnose_hint')[0])

    def test_canary_never_sends_private_cases_even_with_private_egress(self):
        from canary import run
        cfg = json.loads(json.dumps(self.cfg)); cfg['canary'] = {'enabled': True, 'max_calls_per_run': 3}
        cfg['providers']['fake']['data_classes'] = ['public', 'internal', 'private']
        cfg['egress']['person-a']['ma-home']['private'] = ['fake']     # operator allowed private for production
        res = run(self.client(cfg), self.suite([{'id': 'priv', 'task_type': 'diagnose_hint', 'prompt': 'Mail an max@example.org',
                                                  'verify': {'type': 'grounded'}}]), provider='fake', project='ma-home')
        self.assertEqual(res['refused'], [{'id': 'priv', 'why': 'not public data - never sent'}])
        self.assertEqual(tp.Fake.hits, 0)

    def test_wrong_canary_answers_lower_trust(self):
        from canary import run
        cfg = json.loads(json.dumps(self.cfg)); cfg['canary'] = {'enabled': True, 'max_calls_per_run': 4}
        tp.Fake.mode = 'fabricated'
        h = self.client(cfg)
        res = run(h, self.suite(self.CASES), provider='fake', project='ma-home')
        self.assertFalse(any(r['verified'] for r in res['results']))
        rp = RoutePolicy(self.d / 'r.db', None, h, mode='active', min_samples=3)
        self.assertFalse(rp._reliable('fake', 'diagnose_hint')[0])


if __name__ == '__main__':
    unittest.main()
