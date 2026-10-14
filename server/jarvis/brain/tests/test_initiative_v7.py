import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from brain_core import Brain
from cognitive_loop import CognitiveLoop
from initiative import prepare
from autonomy import Queue

class InitiativeTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.folder=Path(tmp.name)
        self.workspace=self.folder/'workspace';self.workspace.mkdir()
        self.brain=Brain(self.folder/'brain.db','person-a',{'ma-home'})
        self.loop=CognitiveLoop(self.brain)
        self.cfg={'enabled':True,'allowed_workspaces':[str(self.workspace)],
                  'allowed_templates':['repo_audit'],'db_path':str(self.folder/'jobs.db')}
        self.loop.expectation('ma-home','service:test','healthy','manual')
        self.loop.observe('ma-home','health','service:test','unhealthy','read-only test',4)

    def test_only_dry_run_by_default(self):
        result=prepare(self.loop,self.cfg,'ma-home',str(self.workspace))
        self.assertEqual(result['eligible'],1)
        self.assertEqual(result['created'],[])
        self.assertFalse((self.folder/'jobs.db').exists())

    def test_permission_and_pause(self):
        with self.assertRaises(PermissionError):
            prepare(self.loop,self.cfg,'ma-home',str(self.folder))
        self.loop.set_paused('ma-home',True)
        self.assertEqual(prepare(self.loop,self.cfg,'ma-home',str(self.workspace),True)['blocked'],'paused')

    def test_explicit_opt_in_and_dedup(self):
        one=prepare(self.loop,self.cfg,'ma-home',str(self.workspace),True)
        two=prepare(self.loop,self.cfg,'ma-home',str(self.workspace),True)
        self.assertEqual(len(one['created']),1)
        self.assertEqual(two['created'],[])
        with Queue(self.cfg['db_path']).connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM jobs').fetchone()[0],1)

    def test_no_queue_when_disabled(self):
        cfg={**self.cfg,'enabled':False}
        self.assertEqual(prepare(self.loop,cfg,'ma-home',str(self.workspace),True)['blocked'],
                         'autonomy disabled')
        self.assertFalse((self.folder/'jobs.db').exists())

if __name__=='__main__':unittest.main()
