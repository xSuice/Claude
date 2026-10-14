"""V10.1 backup + restore probe and inventory smoke test. Offline."""
import json
import os
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server')); sys.path.insert(0, str(ROOT / 'brain-runtime'))
import backup_restore as br
from brain_core import Brain


class BackupRestore(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); self.d = Path(t.name)
        self.brain = Brain(self.d / 'state' / 'b.db', 'person-a', {'ma-home'})
        for i in range(20):
            self.brain.confirm(self.brain.propose('ma-home', f't{i}', 'inhalt', 's')['id'])
        (self.d / 'actions.json').write_text('{"actions": {}}')
        self.cfg = self.d / 'brain.json'
        self.cfg.write_text(json.dumps({'identity': 'person-a', 'allowed_projects': ['ma-home'],
                                        'state_db': 'state/b.db', 'actions': 'actions.json'}))

    def test_backup_probe_counts_and_permissions(self):
        r = br.backup(self.cfg, [], self.d / 'bk')
        self.assertTrue(r['restore_probe_ok'], r)
        self.assertEqual(r['probe']['row_counts']['brain.state_db.sqlite3']['memory'], 20)
        self.assertIn('actions.json', r['configs'])
        self.assertEqual(stat.S_IMODE(Path(r['archive']).stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((self.d / 'bk').stat().st_mode), 0o700)

    def test_restore_never_overwrites_and_detects_tampering(self):
        r = br.backup(self.cfg, [], self.d / 'bk')
        busy = self.d / 'busy'; busy.mkdir(); (busy / 'x').write_text('live')
        with self.assertRaises(FileExistsError):
            br.restore(Path(r['archive']), busy)
        ok = br.restore(Path(r['archive']), self.d / 'r1')
        self.assertTrue(ok['ok']); self.assertEqual(ok['integrity'], {'brain.state_db.sqlite3': 'ok'})
        tampered = self.d / 'evil.tar.gz'
        root = Path(ok['restored_to'])
        (root / 'config' / 'actions.json').write_text('{"actions": {"x": {"argv": ["rm"]}}}')
        with tarfile.open(tampered, 'w:gz') as tar:
            tar.add(root, arcname=root.name)
        bad = br.restore(tampered, self.d / 'r2')
        self.assertFalse(bad['ok']); self.assertEqual(bad['hash_mismatch'], ['config/actions.json'])

    def test_consistent_while_writing(self):
        stop = threading.Event()
        def writer():
            b = Brain(self.d / 'state' / 'b.db', 'person-a', {'ma-home'})
            while not stop.is_set():
                b.propose('ma-home', 'w', 'x', 's')
        th = threading.Thread(target=writer); th.start()
        try:
            r = br.backup(self.cfg, [], self.d / 'bk')
        finally:
            stop.set(); th.join()
        self.assertTrue(r['restore_probe_ok'], r)

    def test_archive_with_path_traversal_is_refused(self):
        evil = self.d / 'trav.tar.gz'
        (self.d / 'payload').write_text('x')
        with tarfile.open(evil, 'w:gz') as tar:
            tar.add(self.d / 'payload', arcname='../../escaped')
        with self.assertRaises(Exception):
            br.restore(evil, self.d / 'r3')
        self.assertFalse((self.d.parent / 'escaped').exists())


class Inventory(unittest.TestCase):
    def test_runs_read_only_and_hides_secrets(self):
        with tempfile.TemporaryDirectory() as h:
            home = Path(h); (home / '.claude').mkdir()
            (home / '.claude' / 'settings.json').write_text(json.dumps({'hooks': {'Stop': [
                {'hooks': [{'type': 'command', 'command': 'python3 /x/experience.py hook --token sk-ant-SECRET123456'}]},
                {'hooks': [{'type': 'command', 'command': 'python3 /x/experience.py hook --token sk-ant-SECRET123456'}]}]}}))
            (home / '.claude.json').write_text(json.dumps({'mcpServers': {'ma-home-brain': {
                'command': 'ssh', 'env': {'API_KEY': 'SECRETVALUE'}}}}))
            before = sorted(str(p) for p in home.rglob('*'))
            p = subprocess.run([sys.executable, str(ROOT / 'server' / 'inventory.py')], capture_output=True, text=True,
                               timeout=120, env={'HOME': h, 'PATH': os.environ['PATH']})
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertNotIn('SECRET', p.stdout)
            d = json.loads(p.stdout)
            self.assertEqual(d['claude_code']['mcp_servers'], {'ma-home-brain': 'stdio'})
            self.assertEqual(d['claude_code']['duplicate_hooks'], ['Stop: python3 experience.py'])
            self.assertEqual(before, sorted(str(p) for p in home.rglob('*')))


if __name__ == '__main__':
    unittest.main()
