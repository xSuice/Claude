"""V16 server CLI end to end through real subprocesses, with a fake `claude` program (same JSON shape)."""
import io
import json
import os
import subprocess
import sys
import tarfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v16_fakes import tmpdir  # noqa: E402

import sandbox  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LINUX = sys.platform == 'linux' and sandbox.available()
FAKE = '''#!/usr/bin/env python3
import os, sys
sys.path.insert(0, %r)
from v16_fakes import FakeClaude, WC_PLAN, wc_steps
code, out, err = FakeClaude(WC_PLAN, wc_steps())(sys.argv, sys.stdin.read(), os.getcwd(), 60)
sys.stdout.write(out); sys.stderr.write(err); sys.exit(code)
''' % str(Path(__file__).resolve().parent)


@unittest.skipUnless(LINUX, 'needs Linux with a sandbox backend')
class Cli(unittest.TestCase):
    def setUp(self):
        self.t = tmpdir(self)
        fake = self.t / 'claude'
        fake.write_text(FAKE)
        os.chmod(fake, 0o700)
        self.cfg = self.t / 'jarvis.json'
        self.cfg.write_text(json.dumps({'identity': 'person-a', 'project': 'jarvis', 'state_dir': str(self.t / 'state'),
                                        'results_dir': str(self.t / 'results'), 'system_db': str(self.t / 'sys' / 'system.db'),
                                        'claude_bin': str(fake), 'router_dir': str(ROOT.parents[3] / 'scripts' / 'router'),
                                        'resources': {'min_mem_mb': 0, 'min_mem_heavy_mb': 0, 'max_psi_mem': 100, 'max_load_per_cpu': 100}}))
        os.chmod(self.cfg, 0o600)
        (self.t / 'sys').mkdir()
        r = self.run_cli('caps', '--discover', '--no-selftest')
        self.assertEqual(r[0], 0)
        for cap in ('python.run', 'python.unittest'):
            subprocess.run([sys.executable, '-c', 'import sys; sys.path.insert(0, %r); from capabilities import Registry; '
                            'Registry(__import__("pathlib").Path(%r), "server").selftest(%r)' % (str(ROOT), str(self.t / 'sys' / 'system.db'), cap)],
                           check=True)

    def run_cli(self, *args, stdin=b''):
        p = subprocess.run([sys.executable, str(ROOT / 'jarvis_cli.py'), '--config', str(self.cfg), *args], input=stdin,
                           capture_output=True, timeout=300)
        if args and args[0] in ('result-tar', 'pc-pull') and p.returncode == 0:
            return p.returncode, p.stdout
        try:
            return p.returncode, json.loads(p.stdout.decode().strip().splitlines()[-1])
        except (ValueError, IndexError):
            self.fail(f'no JSON: {p.stdout[:500]!r} {p.stderr[-1500:]!r}')

    def test_full_cycle(self):
        tb = io.BytesIO()
        with tarfile.open(fileobj=tb, mode='w:gz') as tf:
            data = b'Beispieltext zum Zaehlen'
            ti = tarfile.TarInfo('beispiel.txt'); ti.size = len(data); tf.addfile(ti, io.BytesIO(data))
        req = json.dumps({'request': 'Erstelle ein Python-Werkzeug, das Wörter zählt, mit Tests', 'client_id': 'cli-test-000001',
                          'options': {'origin': 'test'}}).encode() + b'\n' + tb.getvalue()
        code, r = self.run_cli('submit', stdin=req)
        self.assertEqual(code, 0, r)
        job = r['job_id']
        code, r2 = self.run_cli('submit', stdin=req)
        self.assertTrue(r2['duplicate'])
        for _ in range(8):
            self.run_cli('tick', '--max-seconds', '20')
            if self.run_cli('status', job)[1]['state'] in ('done', 'failed', 'partial'):
                break
        st = self.run_cli('status', job)[1]
        self.assertEqual(st['state'], 'done', st)
        res = self.run_cli('result', job)[1]
        self.assertIn('BERICHT.md', res['files'])
        self.assertTrue(res['final'])
        code, raw = self.run_cli('result-tar', job)
        names = tarfile.open(fileobj=io.BytesIO(raw)).getnames()
        self.assertIn('wc.py', names)
        evs = self.run_cli('events', job)[1]['events']
        self.assertTrue(any(e['kind'] == 'finished' for e in evs))
        self.assertTrue((self.t / 'state' / 'work' / job / 'inputs' / 'beispiel.txt').is_file())
        self.assertEqual(self.run_cli('list')[1]['jobs'][0]['id'], job)
        u = self.run_cli('usage')[1]
        self.assertEqual(u['ledger']['claude']['calls_24h'], 3)
        d = self.run_cli('doctor')[1]
        self.assertEqual(d['sandbox_backend'], sandbox.backend())
        self.assertTrue(d['state_dir_private'])

    def test_refusals(self):
        code, r = self.run_cli('submit', stdin=json.dumps({'request': 'token: abcdefghijklmnopqrstuvwxyz123456'}).encode())
        self.assertEqual(code, 3)
        self.assertEqual(self.run_cli('kill', 'on', '--global')[0], 0)
        code, r = self.run_cli('submit', stdin=json.dumps({'request': 'Hallo Welt Auftrag'}).encode())
        self.assertEqual(code, 3)
        self.assertIn('global', self.run_cli('tick')[1]['idle'])
        self.run_cli('kill', 'off', '--global')
        self.assertEqual(self.run_cli('status', 'j-gibt-es-nicht')[0], 3)
        os.chmod(self.cfg, 0o666)
        self.assertEqual(self.run_cli('list')[0], 3)

    def test_bad_input_upload_is_refused(self):
        tb = io.BytesIO()
        with tarfile.open(fileobj=tb, mode='w:gz') as tf:
            ti = tarfile.TarInfo('../../ausbruch.txt'); ti.size = 1; tf.addfile(ti, io.BytesIO(b'x'))
        code, r = self.run_cli('submit', stdin=json.dumps({'request': 'Auftrag mit Datei'}).encode() + b'\n' + tb.getvalue())
        self.assertEqual(code, 2)
        self.assertFalse((self.t.parent / 'ausbruch.txt').exists())


if __name__ == '__main__':
    unittest.main()
