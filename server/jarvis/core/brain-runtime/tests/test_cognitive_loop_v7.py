"""Offline behavioral and security tests. No Claude, external APIs or Internet."""
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from brain_core import Brain
from cognitive_loop import CognitiveLoop
from mcp_server_v5 import Server


class LoopTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.db=Path(temp.name)/'brain.sqlite3'
        self.a=Brain(self.db,'person-a',{'ma-home','notes'})
        self.b=Brain(self.db,'person-b',{'ma-home'})
        self.loop=CognitiveLoop(self.a)
        self.other=CognitiveLoop(self.b)

    def test_health_read_only_and_no_cloud(self):
        h=self.loop.health('ma-home')
        self.assertTrue(h['database_ok'])
        self.assertEqual(h['claude_calls'],0)
        self.assertEqual(h['event_count'],0)
        self.assertFalse(h['is_conscious'])

    def test_observation_dedup_and_change(self):
        one=self.loop.observe('ma-home','availability','web','up','local diagnostic')
        self.assertTrue(one['recorded'])
        again=self.loop.observe('ma-home','availability','web','up','local diagnostic')
        self.assertFalse(again['recorded'])
        changed=self.loop.observe('ma-home','availability','web','down','local diagnostic',4)
        self.assertTrue(changed['recorded'])
        self.assertEqual(self.loop.health('ma-home')['event_count'],2)

    def test_expected_mismatch_and_recovery(self):
        self.loop.expectation('ma-home','service:web','healthy','manual baseline',12)
        self.loop.observe('ma-home','health','service:web','unhealthy','read-only local check',4)
        self.assertEqual(self.loop.health('ma-home')['active_anomalies'],1)
        focus=self.loop.focus('ma-home')['candidates'][0]
        self.assertEqual(focus['type'],'observation_mismatch')
        self.loop.observe('ma-home','health','service:web','healthy','local check')
        self.assertEqual(self.loop.health('ma-home')['active_anomalies'],0)

    def test_expired_expectation_not_alerted(self):
        r=self.loop.expectation('ma-home','service:x','up','baseline')
        with self.a.connection(True) as c:
            c.execute('UPDATE cognitive_expectations SET expires=0 WHERE id=?',(r['id'],))
        self.loop.observe('ma-home','availability','service:x','down','local test')
        self.assertEqual(self.loop.health('ma-home')['active_anomalies'],0)

    def test_authorized_existing_goals_prioritized(self):
        self.a.new_goal('ma-home','low','get result',['step low'],5)
        self.a.new_goal('ma-home','high','get result',['step high'],1)
        focus=self.loop.focus('ma-home')['candidates']
        self.assertEqual(focus[0]['instruction'],'step high')
        self.assertEqual(focus[1]['instruction'],'step low')

    def test_blocked_goal_not_auto_retried(self):
        self.a.new_goal('ma-home','blocked','target',['private credential needed'],1)
        next_step=self.a.next_step('ma-home')
        self.a.report_step('ma-home',next_step['step_id'],'blocked','rights missing')
        self.assertEqual(self.loop.focus('ma-home')['candidates'],[])

    def test_owners_separate_and_project_restricted(self):
        self.loop.expectation('ma-home','private:test','A','authorized')
        self.loop.observe('ma-home','feedback','private:test','B','read only check')
        self.assertEqual(self.other.health('ma-home')['active_anomalies'],0)
        self.assertEqual(self.other.focus('ma-home')['candidates'],[])
        with self.assertRaises(PermissionError):self.other.health('notes')

    def test_pause_prevents_write_and_attention(self):
        self.a.new_goal('ma-home','todo','target',['act'],2)
        self.loop.set_paused('ma-home',True)
        self.assertTrue(self.loop.health('ma-home')['paused'])
        self.assertEqual(self.loop.focus('ma-home')['candidates'],[])
        with self.assertRaises(PermissionError):
            self.loop.observe('ma-home','test','syntax','pass','local')
        with self.assertRaises(PermissionError):
            self.loop.expectation('ma-home','syntax','pass','manual')
        self.assertIsNone(self.loop.cycle('ma-home')['reflection'])
        self.loop.set_paused('ma-home',False)
        self.assertEqual(len(self.loop.focus('ma-home')['candidates']),1)

    def test_consolidation_advisory_never_self_confirms(self):
        first=self.a.propose('ma-home','title','test body','user')
        second=self.a.propose('ma-home','title','test body','user')
        info=self.loop.consolidate('ma-home')
        self.assertEqual(set(info['duplicate_proposal_groups'][0]),{first['id'],second['id']})
        self.assertEqual(self.a.recall('ma-home','title body')['items'],[])
        self.assertFalse(self.loop.cycle('ma-home')['health']['paused'])

    def test_mcp_read_tools_no_sensor_or_expectations(self):
        server=Server({'identity':'person-a','allowed_projects':['ma-home'],'state_db':str(self.db)})
        names={t['name'] for t in server.dispatch({'jsonrpc':'2.0','id':4,'method':'tools/list'})['result']['tools']}
        for name in ('brain_focus','brain_health','brain_reflect'):self.assertIn(name,names)
        for name in ('brain_observe','brain_expect','brain_execute','brain_confirm'):
            self.assertNotIn(name,names)
        ret=server.call('brain_health',{'project':'ma-home'})
        self.assertFalse(ret.get('isError'))
        self.assertEqual(json.loads(ret['content'][0]['text'])['claude_calls'],0)

    def test_paused_supervisor_does_not_scan(self):
        with tempfile.TemporaryDirectory() as temp:
            config=Path(temp)/'config.json'
            root=Path(temp)/'repo';root.mkdir()
            (root/'broken.py').write_text('def not valid\n')
            config.write_text(json.dumps({'identity':'person-a','allowed_projects':['ma-home'],
                                          'state_db':str(self.db)}))
            self.loop.set_paused('ma-home',True)
            cmd=[sys.executable,str(ROOT/'supervisor.py'),'--config',str(config),
                 '--once','--project','ma-home','--project-root',str(root)]
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(self.loop.health('ma-home')['event_count'],0)
            self.assertEqual(json.loads(result.stdout)['observation'],None)

    def test_bad_inputs_disallowed(self):
        for op in (
            lambda:self.loop.observe('ma-home','shell','hello','true','external'),
            lambda:self.loop.observe('ma-home','health','x','up','external',6),
            lambda:self.loop.expectation('ma-home','x','up','evidence',0),
            lambda:self.loop.focus('ma-home',99),
        ):
            with self.assertRaises(ValueError):op()

    def test_concurrent_sensors_and_idempotence(self):
        errors=[]
        def work(i):
            try:self.loop.observe('ma-home','change',f'file:{i}','changed','local')
            except Exception as e:errors.append(e)
        threads=[threading.Thread(target=work,args=(i,)) for i in range(20)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertFalse(errors,str(errors))
        self.assertEqual(self.loop.health('ma-home')['event_count'],20)

if __name__=='__main__':unittest.main()
