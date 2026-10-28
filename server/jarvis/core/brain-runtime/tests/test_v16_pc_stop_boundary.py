"""PC intake must honor the same stop boundary as the scheduler."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v16_fakes import FakeClaude, make_app, run_until, tmpdir
import sandbox

PLAN = {'goal':'Build', 'task_type':'java.mod', 'match_keywords':['java'],
        'deliverables':[{'path':'out.txt','checks':[{'type':'exists'}]}],
        'steps':[{'id':'s1','title':'Build','kind':'pc','capability':'java.build',
                  'args':{},'outputs':['out.txt'],'deps':[]}]}

@unittest.skipUnless(sys.platform == 'linux' and sandbox.available(), 'Linux sandbox required')
class PcStopBoundary(unittest.TestCase):
    def pending(self):
        eng = make_app(tmpdir(self), FakeClaude(PLAN, {}))
        eng.reg.report_pc({'java.build':{'status':'tested','version':'test'}})
        job = eng.submit('Build Java test artifact')['job_id']
        self.assertEqual(run_until(eng, job=job)['state'], 'waiting_pc')
        return eng, job

    def test_no_new_pc_lease_at_any_stop_level(self):
        for level in ('soft', 'exec', 'hard'):
            with self.subTest(level=level):
                eng, job = self.pending()
                (eng.brain.db_path.parent / 'KILL').write_text(level)
                self.assertIsNone(eng.pc_lease(['java.build'], 'test-worker'))
                self.assertEqual(eng.status(job)['state'], 'waiting_pc')

    def test_exec_and_hard_stop_reject_upload_before_workspace_write(self):
        import io
        import tarfile
        for level in ('exec', 'hard'):
            with self.subTest(level=level):
                eng, job = self.pending()
                self.assertIsNotNone(eng.pc_lease(['java.build'], 'test-worker'))
                payload = io.BytesIO()
                with tarfile.open(fileobj=payload, mode='w') as archive:
                    entry = tarfile.TarInfo('out.txt'); entry.size = 4
                    archive.addfile(entry, io.BytesIO(b'late'))
                (eng.brain.db_path.parent / 'KILL').write_text(level)
                with self.assertRaises(PermissionError):
                    eng.pc_complete(job, 's1', True, 'late result', payload.getvalue())
                self.assertFalse((Path(eng._job(job)['workspace']) / 'out.txt').exists())

if __name__ == '__main__':
    unittest.main()
