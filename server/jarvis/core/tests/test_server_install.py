import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SERVER=ROOT/'server'
RUNTIME=ROOT/'brain-runtime'
sys.path.insert(0,str(RUNTIME))
from brain_core import Brain

class TestServer(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.app=self.root/'app'
        self.data=self.root/'data'
        self.conf=self.root/'config'
    def install(self,apply=False):
        cmd=[sys.executable,str(SERVER/'install_linux.py'),'--app-dir',str(self.app),
             '--data-dir',str(self.data),'--config-dir',str(self.conf)]
        if apply:cmd.append('--apply')
        return subprocess.run(cmd,text=True,capture_output=True)
    def test_dryrun_has_no_writes(self):
        p=self.install(); self.assertEqual(p.returncode,0,p.stderr)
        self.assertFalse(self.app.exists()); self.assertFalse(self.conf.exists())
    def test_actual_install_and_mcp(self):
        p=self.install(True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertTrue((self.app/'bin/mcp-person-a').is_file())
        a=json.loads((self.conf/'person-a.json').read_text())
        b=json.loads((self.conf/'person-b.json').read_text())
        self.assertEqual(a['state_db'],b['state_db'])
        self.assertNotIn('source',a)
        self.assertEqual(os.stat(self.conf/'person-a.json').st_mode & 0o777,0o600)
        probe=subprocess.run([sys.executable,str(SERVER/'probe_mcp.py'),
            '--config',str(self.conf/'person-a.json'),'--runtime',str(self.app/'brain-runtime')],
            capture_output=True,text=True)
        self.assertEqual(probe.returncode,0,probe.stderr)
    def test_profiles_do_not_cross_recall(self):
        self.assertEqual(self.install(True).returncode,0)
        a=Brain(self.data/'brain.sqlite3','person-a',{'ma-home'})
        b=Brain(self.data/'brain.sqlite3','person-b',{'ma-home'})
        r=a.propose('ma-home','OpenWorm brain config','Test secret key 123-321','synthetic test')
        a.confirm(r['id'])
        self.assertEqual(len(a.recall('ma-home','OpenWorm brain')['items']),1)
        self.assertEqual(len(b.recall('ma-home','OpenWorm brain')['items']),0)
        shared=a.propose('ma-home','Shared lab notes','Test shared data','synthetic test')
        a.confirm(shared['id'],recipients=['person-b'])
        self.assertEqual(len(b.recall('ma-home','Shared lab notes')['items']),1)
        backup=subprocess.run([sys.executable,str(SERVER/'backup_sqlite.py'),
            '--config',str(self.conf/'person-a.json'),'--out-dir',str(self.root/'backups')],
            capture_output=True,text=True)
        self.assertEqual(backup.returncode,0,backup.stderr)
        self.assertEqual(len(list((self.root/'backups').glob('brain-*.sqlite3'))),1)
    def test_update_preserves_state(self):
        self.assertEqual(self.install(True).returncode,0)
        db=Brain(self.data/'brain.sqlite3','person-a',{'ma-home'})
        r=db.propose('ma-home','Persisted note','Must survive an update','synthetic test')
        db.confirm(r['id'])
        cmd=[sys.executable,str(SERVER/'install_linux.py'),'--app-dir',str(self.app),
             '--data-dir',str(self.data),'--config-dir',str(self.conf),'--apply','--update']
        p=subprocess.run(cmd,text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(len(Brain(self.data/'brain.sqlite3','person-a',{'ma-home'}).recall('ma-home','Persisted note')['items']),1)
        self.assertTrue(list(self.root.glob('app.backup-*')))

if __name__=='__main__':unittest.main()
