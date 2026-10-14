"""Offline acceptance tests; explicitly do NOT benchmark Claude intelligence or cost."""
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'brain-runtime'))
from brain_core import Brain
from mcp_server_v5 import Server


class CognitiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/'state.sqlite3'
        self.alice=Brain(self.db,'person-a',{'ma-home','writing'})
        self.bob=Brain(self.db,'person-b',{'ma-home'})

    def test_proposal_not_recallable_until_confirmed(self):
        r=self.alice.propose('ma-home','Active server port','Active server port 3000', 'verified test-setup')
        self.assertEqual(self.alice.recall('ma-home','server port')['items'],[])
        self.alice.confirm(r['id'])
        self.assertEqual(len(self.alice.recall('ma-home','server port')['items']),1)

    def test_restart_persists(self):
        r=self.alice.propose('ma-home','Database backend','Database SQLite state', 'user-confirmed')
        self.alice.confirm(r['id'])
        fresh=Brain(self.db,'person-a',{'ma-home'})
        self.assertEqual(fresh.recall('ma-home','Database SQLite')['items'][0]['id'],r['id'])

    def test_user_and_project_isolation(self):
        r=self.alice.propose('ma-home','Private server config','secrettext rocket launcher','synthetic')
        self.alice.confirm(r['id'])
        self.assertEqual(self.bob.recall('ma-home','server config')['items'],[])
        with self.assertRaises(PermissionError):self.bob.recall('writing','server config')
        self.assertEqual(self.alice.recall('writing','server config')['items'],[])
        with self.assertRaises(PermissionError):self.bob.retract(r['id'])

    def test_authorized_share_only(self):
        r=self.alice.propose('ma-home','Shared local dashboard','Local dashboard available', 'synthetic')
        self.alice.confirm(r['id'],recipients=['person-b'])
        self.assertEqual(len(self.bob.recall('ma-home','local dashboard')['items']),1)

    def test_retraction_immediate(self):
        r=self.alice.propose('ma-home','Previous host IP','Host IP 192.0.2.23', 'synthetic')
        self.alice.confirm(r['id'],recipients=['person-b'])
        self.assertTrue(self.bob.recall('ma-home','Host IP')['items'])
        self.alice.retract(r['id'])
        self.assertFalse(self.bob.recall('ma-home','Host IP')['items'])

    def test_supersede_atomic(self):
        old=self.alice.propose('ma-home','Port config','Service port 3000','test')
        self.alice.confirm(old['id'])
        new=self.alice.propose('ma-home','Port config','Service port 8080','test')
        self.alice.confirm(new['id'],supersede=old['id'])
        texts=[i['content'] for i in self.alice.recall('ma-home','Port config')['items']]
        self.assertIn('Service port 8080',texts)
        self.assertNotIn('Service port 3000',texts)

    def test_wrong_supersede_fails_without_partial_commit(self):
        new=self.alice.propose('ma-home','Host config','Host moved to port 80','test')
        with self.assertRaises(ValueError):self.alice.confirm(new['id'],supersede='bad-id')
        self.assertEqual(self.alice.recall('ma-home','Host config')['items'],[])

    def test_recall_budget(self):
        for i in range(7):
            r=self.alice.propose('ma-home','Config service','Service config sample '+str(i)+' '*100,'test')
            self.alice.confirm(r['id'])
        out=self.alice.recall('ma-home','service config',max_chars=300)
        self.assertLessEqual(out['chars'],300)

    def test_goal_persists_and_progress_idempotent(self):
        goal=self.alice.new_goal('ma-home','Repair startup','Unit tests green', ['Inspect failure','Fix and test'],2)
        step=self.alice.next_step('ma-home')
        self.assertEqual(step['instruction'],'Inspect failure')
        once=self.alice.report_step('ma-home',step['step_id'],'reported_done','test artifact abc')
        twice=self.alice.report_step('ma-home',step['step_id'],'reported_done','duplicate')
        self.assertTrue(once['changed'])
        self.assertFalse(twice['changed'])
        self.assertEqual(self.alice.next_step('ma-home')['instruction'],'Fix and test')
        self.assertEqual(self.bob.list_goals('ma-home')['goals'],[])

    def test_blocked_step_not_silently_retried(self):
        self.alice.new_goal('ma-home','Stuck', 'recover safely', ['Check credential'],1)
        s=self.alice.next_step('ma-home')
        self.alice.report_step('ma-home',s['step_id'],'blocked','no rights')
        self.assertIsNone(self.alice.next_step('ma-home')['step'])

    def test_unverified_not_used_for_improvement(self):
        for _ in range(4):
            self.alice.episode('ma-home','debug','test failed','failure','synthetic log')
        self.assertFalse(self.alice.tick('ma-home')['new_suggestions'])
        self.assertTrue(all(x['verified']==0 for x in self.alice.insights('ma-home')['episodes']))

    def test_verified_repeat_generates_one_suggestion(self):
        ids=[self.alice.episode('ma-home','debug','unit test failed','failure','log')['id'] for _ in range(3)]
        for key in ids:self.alice.verify_episode(key)
        self.assertEqual(len(self.alice.tick('ma-home')['new_suggestions']),1)
        self.assertEqual(self.alice.tick('ma-home')['new_suggestions'],[])
        self.assertEqual(self.bob.insights('ma-home')['episodes'],[])

    def test_concurrent_writes(self):
        errors=[]
        def write(i):
            try:
                self.alice.propose('ma-home',f'Title {i}',f'Content {i}', 'synthetic')
            except Exception as e:errors.append(e)
        threads=[threading.Thread(target=write,args=(i,)) for i in range(20)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertFalse(errors,str(errors))
        self.assertEqual(len(self.alice.pending('ma-home',20)['proposals']),20)

    def test_mcp_no_confirm_and_no_shell(self):
        config={'identity':'person-a','allowed_projects':['ma-home'],
                'state_db':str(self.db),'research_tools':False}
        server=Server(config)
        names={t['name'] for t in server.dispatch({'jsonrpc':'2.0','id':1,'method':'tools/list'})['result']['tools']}
        self.assertNotIn('brain_confirm',names)
        self.assertNotIn('brain_execute',names)
        self.assertIn('brain_cycle',names)
        result=server.call('brain_propose_memory',{'project':'ma-home','title':'Test','content':'irrelevant','source':'test'})
        record=json.loads(result['content'][0]['text'])
        self.assertEqual(record['status'],'proposed')
        self.assertTrue(server.call('brain_confirm',{'id':record['id']})['isError'])

    def test_stdio_smoke(self):
        config=Path(self.tmp.name)/'config.json'
        config.write_text(json.dumps({'identity':'person-a','allowed_projects':['ma-home'],
                         'state_db':str(self.db),'research_tools':False}),encoding='utf-8')
        data='\n'.join(json.dumps(x) for x in [
            {'jsonrpc':'2.0','id':1,'method':'initialize','params':{}},
            {'jsonrpc':'2.0','id':2,'method':'tools/list'},
            {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'brain_insights','arguments':{'project':'ma-home'}}},
        ])+'\n'
        proc=subprocess.run([sys.executable,str(ROOT/'brain-runtime'/'mcp_server_v5.py'),'--config',str(config)],
                            input=data,text=True,capture_output=True,timeout=15)
        self.assertEqual(proc.returncode,0,proc.stderr)
        messages=[json.loads(s) for s in proc.stdout.splitlines()]
        self.assertEqual([x['id'] for x in messages],[1,2,3])
        self.assertEqual(messages[0]['result']['serverInfo']['version'],'0.10.0')

if __name__=='__main__':unittest.main()
