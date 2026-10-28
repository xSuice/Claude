"""CLI-Ebene der Prio-1-Pakete (router, activity, councils, knowledge): echte Prozessaufrufe wie Brücke/Cron.
Fängt Fehler, die Engine-Tests nicht sehen (z. B. fehlende Imports im CLI)."""
import io
import json
import os
import sys
import tarfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_v16_cli import Cli, LINUX  # noqa: E402


@unittest.skipUnless(LINUX, 'needs Linux with a sandbox backend')
class CliPrio1(Cli):
    def setUp(self):
        super().setUp()
        cfg = json.loads(self.cfg.read_text())
        cfg['knowledge_dir'] = str(self.t / 'vault')
        self.cfg.write_text(json.dumps(cfg))
        os.chmod(self.cfg, 0o600)

    def test_full_cycle(self):   # geerbter Volltest hier nicht doppelt ausführen
        pass

    def test_prio1_commands(self):
        tb = io.BytesIO()
        with tarfile.open(fileobj=tb, mode='w:gz'):
            pass
        req = json.dumps({'request': 'Erstelle ein Python-Werkzeug, das Wörter zählt, mit Tests', 'client_id': 'cli-prio1-0001',
                          'options': {'origin': 'test'}}).encode() + b'\n' + tb.getvalue()
        code, r = self.run_cli('submit', stdin=req)
        self.assertEqual(code, 0, r)
        job = r['job_id']
        for _ in range(8):
            self.run_cli('tick', '--max-seconds', '20')
            if self.run_cli('status', job)[1]['state'] in ('done', 'failed', 'partial'):
                break
        self.assertEqual(self.run_cli('status', job)[1]['state'], 'done')
        code, ro = self.run_cli('router')
        self.assertEqual(code, 0, ro)
        self.assertEqual(ro['mode'], 'shadow')
        self.assertEqual(ro['violation_count'], 0)
        self.assertEqual(self.run_cli('router-backtest')[0], 0)
        code, ac = self.run_cli('activity', '--since', '0')
        self.assertEqual(code, 0, ac)
        self.assertTrue(ac['events'])
        self.assertEqual(self.run_cli('councils')[0], 0)
        code, kn = self.run_cli('knowledge')
        self.assertEqual(code, 0, kn)
        cid = next(c['id'] for c in kn['candidates'] if c['state'] == 'proposed')
        env_worker = {**os.environ, 'JARVIS_WORKER': '1'}
        import subprocess
        p = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'jarvis_cli.py'), '--config', str(self.cfg),
                            'knowledge', '--op', 'approve', '--id', str(cid)], capture_output=True, env=env_worker, timeout=60)
        self.assertNotEqual(p.returncode, 0)                         # Claude-Worker dürfen nichts freigeben
        code, w = self.run_cli('knowledge', '--op', 'approve', '--id', str(cid), '--by', 'portal:fremd')
        self.assertEqual(code, 0, w)
        self.assertEqual(w['state'], 'written')
        self.assertTrue(Path(w['note']).is_file())
        self.assertIn('approved_by: cli:', Path(w['note']).read_text(encoding='utf-8'))   # portal:-Behauptung ohne Brücke zählt nicht


if __name__ == '__main__':
    unittest.main()
