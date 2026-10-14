"""V7.1 regression tests for defects found in the V7 review. Offline only."""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain_core import Brain
from cognitive_loop import CognitiveLoop
from initiative import prepare
from autonomy import Queue, validated
from mcp_server_v5 import Server


class V71Fixes(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.ws = self.dir / 'ws'; self.ws.mkdir()
        self.brain = Brain(self.dir / 'b.db', 'person-a', {'ma-home'})
        self.loop = CognitiveLoop(self.brain)

    # Defect 1: an unchanged state seen before an expectation existed was never compared.
    def test_unchanged_state_checked_against_new_expectation(self):
        self.loop.observe('ma-home', 'health', 'service:web', 'unhealthy', 'sensor', 4)
        self.loop.expectation('ma-home', 'service:web', 'healthy', 'baseline')
        r = self.loop.observe('ma-home', 'health', 'service:web', 'unhealthy', 'sensor', 4)
        self.assertFalse(r['recorded'])            # still deduplicated
        self.assertEqual(r['anomalies'], 1)        # but detected
        again = self.loop.observe('ma-home', 'health', 'service:web', 'unhealthy', 'sensor', 4)
        self.assertEqual(again['anomalies'], 0)    # no duplicate anomaly
        self.assertEqual(self.loop.health('ma-home')['active_anomalies'], 1)

    # Defect 2: severe anomalies were invisible to initiative when 3 goals outranked them.
    def test_severe_anomaly_not_crowded_out_by_goals(self):
        for i in range(3):
            self.brain.new_goal('ma-home', f'g{i}', 'r', ['s'], priority=1)
        self.loop.expectation('ma-home', 'service:db', 'healthy', 'baseline')
        self.loop.observe('ma-home', 'health', 'service:db', 'down', 'sensor', 5)
        cfg = {'enabled': True, 'allowed_workspaces': [str(self.ws.resolve())],
               'allowed_templates': ['repo_audit'], 'db_path': str(self.dir / 'q.db')}
        self.assertEqual(prepare(self.loop, cfg, 'ma-home', str(self.ws))['eligible'], 1)

    # Defect 3: bare mode never uses the Pro/Max login and silently switches to API billing.
    def test_bare_mode_default_off_and_requires_cost_cap(self):
        base = {'allowed_workspaces': [str(self.ws)]}
        self.assertFalse(validated(dict(base), self.dir / 'c.json')['bare_mode'])
        with self.assertRaises(ValueError):
            validated({**base, 'bare_mode': True}, self.dir / 'c.json')
        ok = validated({**base, 'bare_mode': True, 'max_estimated_api_usd_per_run': 0.5}, self.dir / 'c.json')
        self.assertTrue(ok['bare_mode'])

    # Defect 4: a crashed worker left a job 'running' forever with no operator command.
    def test_reconcile_stale_running_jobs(self):
        cfg = validated({'enabled': True, 'allowed_workspaces': [str(self.ws)],
                         'minimum_gap_seconds': 0, 'db_path': str(self.dir / 'q.db')}, self.dir / 'c.json')
        q = Queue(cfg['db_path'])
        q.enqueue(cfg, 'person-a', 'ma-home', 'repo_audit', str(self.ws))
        job = q.claim(cfg, now=int(time.time()) - 10_000)
        self.assertEqual(q.reconcile(cfg), {'reconciled': [job['id']]})
        self.assertEqual(q.listing()[0]['status'], 'failed')
        self.assertEqual(q.reconcile(cfg), {'reconciled': []})

    # Improvement: tool allowlist cuts the MCP schema loaded into every session.
    def test_tool_allowlist(self):
        s = Server({'identity': 'person-a', 'allowed_projects': ['ma-home'],
                    'state_db': str(self.dir / 'b.db'), 'tools': ['brain_lookup', 'brain_focus']})
        names = [t['name'] for t in s.dispatch({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})['result']['tools']]
        self.assertEqual(names, ['brain_lookup', 'brain_focus'])
        r = s.call('brain_health', {'project': 'ma-home'})
        self.assertTrue(r.get('isError'))
        with self.assertRaises(ValueError):
            Server({'identity': 'person-a', 'allowed_projects': ['ma-home'],
                    'state_db': str(self.dir / 'b.db'), 'tools': ['brain_shell']})

    # Improvement: German compound words were not found by keyword recall.
    def test_recall_compound_prefix(self):
        p = self.brain.propose('ma-home', 'Routerkonfiguration', 'Haiku für Übersetzungen', 'note')
        self.brain.confirm(p['id'])
        self.assertEqual(len(self.brain.recall('ma-home', 'Router')['items']), 1)
        self.assertEqual(len(self.brain.recall('ma-home', 'Rou')['items']), 0)  # no tiny-prefix noise


if __name__ == '__main__':
    unittest.main()
