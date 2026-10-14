#!/usr/bin/env python3
"""V11.1 audit measurement: identical scenarios against a runtime directory (V11 or V11.1).

  python3 measure_v111.py RUNTIME_DIR      (RUNTIME_DIR/tests must contain the V11.1 fake server tests)

Scenarios (helper = local fake server, SIMULATED - no real provider):
  quality   5 helper answer kinds through the real order chain: only 'grounded' is a correct result.
            false_done = a step closed as verified although the answer was empty/ungrounded/
            fabricated/injected (= hidden rework later).
  shadow    router names a helper, mode shadow: number of real helper requests.
  budget    10 parallel requests against daily_call_budget=3: requests that reached the provider.
"""
import json
import shutil
import sys
import threading
import unittest
from pathlib import Path

RT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(RT)); sys.path.insert(0, str(RT / 'tests'))
import test_v11_providers as tp            # noqa: E402
from test_v11_autopilot_chain import ChainBase   # noqa: E402
from route_policy import RoutePolicy       # noqa: E402
RES = {}


class M(ChainBase):
    def clean(self):
        for p in self.d.iterdir():
            if p.name != 'fake.key':
                shutil.rmtree(p) if p.is_dir() else p.unlink()

    def runTest(self):
        q = {}
        for mode in ('grounded', 'ok', 'empty', 'fabricated', 'inject'):
            self.clean(); tp.Fake.mode, tp.Fake.hits = mode, 0
            d = self.world()
            crash = None
            try:
                d.tick(); (self.ws / 'web.state').write_text('failed'); d.tick(); d.tick()
            except Exception as e:  # noqa: BLE001 - a crash is a measured result, not a script error
                crash = f'{type(e).__name__}: {str(e)[:60]}'
            with self.b.connection() as db:
                st = db.execute('SELECT status FROM steps').fetchone()[0]
            with self.ex.helpers._conn() as c:
                v = c.execute('SELECT SUM(verified=1) FROM helper_calls').fetchone()[0] or 0
            q[mode] = {'step': st, 'helper_counted_success': v, 'requests': tp.Fake.hits, 'crash': crash}
        RES['quality'] = q
        RES['quality_summary'] = {
            'correct_done': int(q['grounded']['step'] == 'verified'),
            'false_done': sum(q[m]['step'] == 'verified' for m in ('ok', 'empty', 'fabricated', 'inject')),
            'crashes': sum(bool(q[m]['crash']) for m in q),
            'false_trust_points': sum(q[m]['helper_counted_success'] for m in ('ok', 'empty', 'fabricated', 'inject'))}
        # shadow
        self.clean(); tp.Fake.mode, tp.Fake.hits = 'grounded', 0
        r = self.d / 'router.py'; r.write_text('import sys,json;json.load(sys.stdin);print(json.dumps({"target":"helper:fake"}))')
        rp = RoutePolicy(self.d / 'r.db', [sys.executable, str(r)], self.client(), mode='shadow', provider_order=['fake'])
        rp._reliable = lambda p, t: (True, 'x')
        d = rp.decide({'task_type': 'diagnose_hint', 'risk': 'read', 'data_class': 'internal', 'size_chars': 1,
                       'has_procedure': False, 'fallback': 'claude'}, 'ma-home')
        RES['shadow'] = {'executed': d['executed'], 'would_call_helper': d['executed'].startswith('helper')}
        # parallel budget
        self.clean(); tp.Fake.mode, tp.Fake.hits = 'slowish', 0
        cfg = json.loads(json.dumps(self.cfg)); cfg['daily_call_budget'] = 3
        cfg['providers']['fake']['limits'] = {'rpm': 1000, 'rpd': 1000, 'tpd': 10 ** 9}
        def go():
            try:
                self.client(cfg).call('fake', 'diagnose_hint', 'x', project='ma-home')
            except Exception:  # noqa: BLE001
                pass
        ts = [threading.Thread(target=go) for _ in range(10)]
        [t.start() for t in ts]; [t.join() for t in ts]
        RES['parallel_budget'] = {'budget': 3, 'requests_reached_provider': tp.Fake.hits}
        # token budget 0
        self.clean(); tp.Fake.mode, tp.Fake.hits = 'ok', 0
        cfg = json.loads(json.dumps(self.cfg)); cfg['daily_token_budget'] = 0
        try:
            self.client(cfg).call('fake', 'diagnose_hint', 'x', project='ma-home')
        except Exception:  # noqa: BLE001
            pass
        RES['token_budget_zero'] = {'requests_reached_provider': tp.Fake.hits}


tp.Base.setUpClass.__func__(M)
try:
    r = unittest.TextTestRunner(stream=open('/dev/null', 'w')).run(M())
    if not r.wasSuccessful():
        raise SystemExit(str(r.errors or r.failures))
finally:
    tp.Base.tearDownClass.__func__(M)
print(json.dumps(RES, indent=1, ensure_ascii=False))
