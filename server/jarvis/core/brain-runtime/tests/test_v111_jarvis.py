"""V11.1 laptop-server additions: root-cause evidence (top consumers), honest scoreboard, canary suite,
resource-limited unit, CLI. Offline."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'tests'))
from performance_intelligence import PerfIntel, Collector
from helper_verify import verify
import scoreboard
import test_v11_providers as tp
from test_v11_autopilot_chain import ChainBase

PY = sys.executable


class RootCause(unittest.TestCase):
    def test_busy_process_named_as_top_cpu_consumer_only_under_pressure(self):
        d = Path(tempfile.mkdtemp())
        busy = subprocess.Popen([PY, '-c', 'while True: pass'])
        self.addCleanup(lambda: (busy.kill(), busy.wait()))
        hot = PerfIntel(d / 'p.db', Collector(disk_paths=[]), limits={'psi_cpu_some': -1.0, 'load1_per_cpu': -1.0})
        hot.sample(1000); time.sleep(1.0); hot.sample(1060); time.sleep(1.0); r = hot.sample(1120)
        names = [x['name'] for x in hot.top['cpu_pct']]
        comm = Path(f'/proc/{busy.pid}/comm').read_text().strip()
        self.assertIn(comm, names[:3])
        self.assertTrue(any('Größter Verbraucher' in c['hint'] for c in hot.causes()))
        with hot._conn() as c:
            ev = json.loads(c.execute("SELECT evidence FROM perf_events WHERE cond='cpu' AND kind='enter'").fetchone()[0])
        self.assertIn('top', ev)
        cold = PerfIntel(d / 'q.db', Collector(disk_paths=[]), limits={'psi_cpu_some': 1e9, 'load1_per_cpu': 1e9,
                                                                         'mem_avail_pct': -1, 'psi_mem_some': 1e9, 'swap_in_ps': 1e9})
        cold.sample(1000); cold.sample(1060)
        self.assertIsNone(cold.top)                  # no pressure -> no process scan at all (laptop: no extra work)


class Verifier(unittest.TestCase):
    CTX = 'Diagnosepaket\n- Log: nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)'

    def test_correct_cause_required_when_known(self):
        q = 'bind() to 0.0.0.0:80 failed (98: Address already in use)'
        right = json.dumps({'cause': 'Port 80 ist bereits belegt.', 'evidence': [{'quote': q}]})
        wrong = json.dumps({'cause': 'Die Festplatte ist voll gelaufen.', 'evidence': [{'quote': q}]})
        spec = {'type': 'grounded', 'cause_any': ['port', 'belegt']}
        self.assertTrue(verify(spec, right, self.CTX, False)[0])
        self.assertEqual(verify(spec, wrong, self.CTX, False), (False, 'grounded but wrong cause'))
        self.assertFalse(verify(spec, right, self.CTX, True)[0])           # suspicious always loses
        self.assertFalse(verify({'type': 'nonsense'}, right, self.CTX, False)[0])  # unknown verifier: fail closed
        for kind in ({'type': 'grounded'}, {'type': 'contains', 'all': ['x']}, {'type': 'json_keys', 'keys': ['a']}):
            self.assertEqual(verify(kind, '  ', self.CTX, False), (False, 'empty answer'))
        self.assertTrue(verify(spec, '```json\n' + right + '\n```', self.CTX, False)[0])

    def test_example_suite_is_public_and_complete(self):
        from provider_adapter import classify
        s = json.loads((ROOT / 'canary-suite.example.json').read_text())
        self.assertGreaterEqual(len(s['cases']), 10)
        for c in s['cases']:
            self.assertEqual(classify(c['prompt'], 'public'), 'public')
            self.assertTrue(c['verify']['cause_any'])


class CanaryExample(tp.Base):
    def test_generic_answers_fail_the_example_suite(self):
        from canary import run
        cfg = json.loads(json.dumps(self.cfg)); cfg['canary'] = {'enabled': True, 'max_calls_per_run': 10}
        cfg['providers']['fake']['limits']['rpm'] = 20
        tp.Fake.mode = 'grounded'   # cites a real line, but names no specific cause
        res = run(self.client(cfg), ROOT / 'canary-suite.example.json', provider='fake', project='ma-home')
        self.assertEqual(len(res['results']), 10); self.assertEqual(res['verified_rate'], 0.0)


class Score(ChainBase):
    def test_scoreboard_attributes_verified_steps_and_counts_resources(self):
        tp.Fake.mode = 'grounded'
        d = self.world()
        d.tick(); (self.ws / 'web.state').write_text('failed'); d.tick(); d.tick()
        sb = scoreboard.build(self.b, 7, helpers_db=self.d / 'h.db')
        self.assertEqual(sb['verified_steps'], {'total': 1, 'local': 0, 'helper': 1, 'claude': 0})
        self.assertEqual(sb['helpers']['verified_ok'], 1); self.assertEqual(sb['helpers']['tokens'], 150)
        self.assertEqual(sb['failures']['anomalies'], 1)
        self.assertEqual(sb['kpi']['share_without_claude'], 1.0)


class Cli(unittest.TestCase):
    def test_unit_limits_and_scoreboard_cli(self):
        d = Path(tempfile.mkdtemp()); (d / 'ws').mkdir(); (d / 'state').mkdir()
        (d / 'brain.json').write_text(json.dumps({'state_db': 'state/brain.db', 'identity': 'person-a', 'allowed_projects': ['ma-home']}))
        (d / 'actions.json').write_text(json.dumps({'actions': {'ok': {'argv': ['/bin/true']}}}))
        (d / 'daemon.json').write_text(json.dumps({'brain_config': 'brain.json', 'actions': 'actions.json', 'workspace': 'ws',
                                                   'project': 'ma-home'}))
        run = lambda *a: subprocess.run([PY, str(ROOT / 'daemon.py'), '--config', str(d / 'daemon.json'), *a],  # noqa: E731
                                        capture_output=True, text=True, timeout=60)
        u = run('unit')
        for k in ('CPUWeight=20', 'IOWeight=20', 'MemoryHigh=384M', 'MemoryMax=512M', 'NoNewPrivileges=yes'):
            self.assertIn(k, u.stdout)
        self.assertEqual(run('once').returncode, 0)
        sb = json.loads(run('scoreboard').stdout)
        self.assertEqual(sb['verified_steps']['total'], 0); self.assertIn('kpi', sb)
        self.assertEqual(run('canary', '--provider', 'x', '--suite', 'y').returncode, 1)   # no providers -> refused


if __name__ == '__main__':
    unittest.main()
