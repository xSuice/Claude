import json
import os
import sqlite3
import stat
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from autonomy import DEFAULT, Queue, TEMPLATES, validated, command, run_once, load_config

class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.repo=self.root/'MA Home'
        self.repo.mkdir()
        self.cfg=validated({'enabled':True,'allowed_workspaces':[str(self.repo)],
                    'minimum_gap_seconds':0,'max_jobs_per_day':2,
                    'claude_binary':'python3','allowed_templates':list(TEMPLATES)},self.root/'conf.json')
        self.q=Queue(self.cfg['db_path'])

    def test_disable_by_default(self):
        cfg={**self.cfg,'enabled':False}
        with self.assertRaises(PermissionError):
            self.q.enqueue(cfg,'person-a','ma-home','repo_audit',self.repo)
        self.assertFalse(run_once(cfg,self.q)['started'])

    def test_whitelist(self):
        with self.assertRaises(PermissionError):
            self.q.enqueue(self.cfg,'person-a','ma-home','repo_audit',self.root)
        with self.assertRaises(PermissionError):
            self.q.enqueue({**self.cfg,'allowed_templates':['knowledge_audit']},
                           'person-a','ma-home','repo_audit',self.repo)
        with self.assertRaises(ValueError):
            self.q.enqueue(self.cfg,'../person-a','ma-home','repo_audit',self.repo)

    def test_claim_atomic_and_daily_quota(self):
        ids=[self.q.enqueue(self.cfg,'person-a','ma-home',t,self.repo) for t in TEMPLATES]
        a=self.q.claim(self.cfg,now=100000)
        b=self.q.claim(self.cfg,now=100001)
        self.assertEqual(a['id'],ids[0])
        self.assertEqual(b['id'],ids[1])
        self.assertIsNone(self.q.claim(self.cfg,now=100002))
        self.q.finish(a['id'],True,0,100,'done')
        with self.q.connect() as c:
            statuses={r['id']:r['status'] for r in c.execute('SELECT id,status FROM jobs')}
        self.assertEqual(statuses[ids[0]],'done')
        self.assertEqual(statuses[ids[2]],'queued')

    def test_duplicate_inflight_submission_reuses_job(self):
        first=self.q.enqueue(self.cfg,'person-a','ma-home','repo_audit',self.repo)
        again=self.q.enqueue(self.cfg,'person-a','ma-home','repo_audit',self.repo)
        self.assertEqual(first,again)
        self.assertEqual(len(self.q.listing()),1)

    def test_cooldown(self):
        cfg={**self.cfg,'minimum_gap_seconds':3600}
        self.q.enqueue(cfg,'person-a','ma-home','repo_audit',self.repo)
        self.q.enqueue(cfg,'person-a','ma-home','repo_audit',self.repo)
        self.assertIsNotNone(self.q.claim(cfg,now=100000))
        self.assertIsNone(self.q.claim(cfg,now=100010))

    def test_worker_fake_claude_output(self):
        self.q.enqueue(self.cfg,'person-a','ma-home','quality_review',self.repo)
        def fake_runner(cmd,cwd,limit):
            self.assertIn('--max-turns',cmd)
            self.assertIn('--permission-mode',cmd)
            self.assertEqual(cmd[cmd.index('--tools')+1],'Read,Glob,Grep')
            self.assertIn('--no-session-persistence',cmd)
            self.assertEqual(cwd,str(self.repo))
            return 0,json.dumps({'result':'One supported finding','usage':{'input_tokens':100,'output_tokens':20}}),''
        value=run_once(self.cfg,self.q,fake_runner)
        self.assertTrue(value['success'])
        result=self.q.listing()[0]
        self.assertEqual(result['status'],'done')
        self.assertEqual(result['excerpt'],'One supported finding')
        self.assertEqual(json.loads(result['model_usage'])['usage']['input_tokens'],100)

    def test_actual_subprocess_with_fake_claude_binary(self):
        executable=self.root/'fake-claude'
        executable.write_text('#!/usr/bin/env python3\nimport json\nprint(json.dumps({"result":"verified fake process","usage":{"input_tokens":44}}))\n')
        executable.chmod(0o700)
        cfg={**self.cfg,'claude_binary':str(executable)}
        self.q.enqueue(cfg,'person-a','ma-home','repo_audit',self.repo)
        result=run_once(cfg,self.q)
        self.assertTrue(result['success'],self.q.listing()[0]['error'])
        self.assertEqual(self.q.listing()[0]['excerpt'],'verified fake process')

    def test_failed_run_not_retried(self):
        self.q.enqueue(self.cfg,'person-a','ma-home','repo_audit',self.repo)
        outcome=run_once(self.cfg,self.q,lambda *_:(3,'','permission denied'))
        self.assertFalse(outcome['success'])
        self.assertEqual(self.q.listing()[0]['status'],'failed')
        self.assertFalse(run_once(self.cfg,self.q)['started'])

    def test_no_unapproved_args(self):
        with self.assertRaises(ValueError):
            validated({'enabled':True,'allowed_workspaces':[str(self.repo)],'unsafe':True},self.root/'c.json')
        with self.assertRaises(ValueError):
            validated({'enabled':True,'allowed_workspaces':[str(self.repo)],'max_turns':100000},self.root/'c.json')

    @unittest.skipUnless(os.name=='posix','POSIX file mode test')
    def test_private_config_required(self):
        f=self.root/'config.json'
        f.write_text(json.dumps({'allowed_workspaces':[str(self.repo)]}))
        os.chmod(f,0o644)
        with self.assertRaises(PermissionError):load_config(f)
        os.chmod(f,0o600)
        self.assertFalse(load_config(f)['enabled'])

if __name__=='__main__':unittest.main()
