"""V9 MCP wiring: Claude can plan and bind, but only to allowlisted actions; no execution via MCP."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mcp_server_v5 import Server

PY = sys.executable


class WiringTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); d = Path(t.name)
        (d / 'ws').mkdir()
        (d / 'actions.json').write_text(json.dumps({'actions': {
            'touch': {'argv': [PY, '-c', "open('x','w')"], 'cwd': '.', 'auto': True},
            'has-x': {'argv': [PY, '-c', "import os,sys;sys.exit(0 if os.path.exists('x') else 1)"], 'cwd': '.', 'auto': True},
            'audit': {'claude_template': 'repo_audit'}}}))
        (d / 'actions.json').chmod(0o600)
        self.s = Server({'identity': 'person-a', 'allowed_projects': ['ma-home'], 'state_db': str(d / 'b.db'),
                         'actions': str(d / 'actions.json'), 'workspace': str(d / 'ws')})
        self.d = d

    def call(self, name, **args):
        r = self.s.call(name, args)
        return r, (None if r.get('isError') else json.loads(r['content'][0]['text']))

    def test_plan_bind_and_execute_locally(self):
        _, g = self.call('brain_create_goal', project='ma-home', title='Datei', desired_result='x existiert',
                         steps=['x anlegen'])
        _, nxt = self.call('brain_next_step', project='ma-home')
        r, b = self.call('brain_bind_step', project='ma-home', step_id=nxt['step_id'], action='touch', check='has-x')
        self.assertEqual(b['state'], 'ready')
        self.assertFalse((self.d / 'ws' / 'x').exists())  # binding never executes
        bad, _ = self.call('brain_bind_step', project='ma-home', step_id=nxt['step_id'], action='rm', check='has-x')
        self.assertTrue(bad.get('isError'))
        self.s.executive.run_once('ma-home')  # what the systemd timer does
        _, ag = self.call('brain_agenda', project='ma-home')
        self.assertEqual(ag['bindings'][0]['status'], 'verified')
        self.assertEqual(ag['actions'], {'touch': 'local auto', 'has-x': 'local auto', 'audit': 'claude needs-approval'})
        names = [t['name'] for t in self.s.dispatch({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})['result']['tools']]
        self.assertIn('brain_bind_step', names)
        self.assertFalse(any('run' in n or 'exec' in n for n in names))  # no execution tool for the model


if __name__ == '__main__':
    unittest.main()
