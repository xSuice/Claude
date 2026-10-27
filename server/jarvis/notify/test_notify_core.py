import sys,unittest,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).parent))
import notify_core as N
NOW=1_000_000
def inc(i,age_min,cls='STALE_AGENT',subj='jarvis-x'):return {'incident_id':i,'classification':cls,'subject':subj,'opened_ts':NOW-age_min*60,'state':'open'}
def job(i,st,fin):return {'id':i,'state':st,'finished':fin}

class First(unittest.TestCase):
    def test_first_run_sets_baseline_without_flood(self):
        msgs,st=N.plan([inc('a',500)],[job('j1','done',NOW-100)],None,NOW)
        self.assertEqual(msgs,[]);self.assertIn('j1',st['jobs_seen']);self.assertEqual(st['incidents_notified'],{'a':NOW})

class Incidents(unittest.TestCase):
    base={'jobs_seen':[],'incidents_notified':{}}
    def test_young_incident_not_sent(self):
        msgs,_=N.plan([inc('a',119)],[],dict(self.base),NOW);self.assertEqual(msgs,[])
    def test_old_incident_sent_once(self):
        msgs,st=N.plan([inc('a',121)],[],dict(self.base),NOW)
        self.assertEqual(len(msgs),1);self.assertEqual(msgs[0]['priority'],4);self.assertIn('STALE_AGENT',msgs[0]['title'])
        msgs2,_=N.plan([inc('a',200)],[],st,NOW+3600);self.assertEqual(msgs2,[])
    def test_resolved_incident_reports_fixed_once(self):
        _,st=N.plan([inc('a',121)],[],dict(self.base),NOW)
        msgs,st2=N.plan([],[],st,NOW+60);self.assertEqual(len(msgs),1);self.assertIn('behoben',msgs[0]['title'].lower())
        msgs3,_=N.plan([],[],st2,NOW+120);self.assertEqual(msgs3,[])

class Jobs(unittest.TestCase):
    def test_new_finished_job_sent_with_state_only(self):
        st={'jobs_seen':['j0'],'incidents_notified':{}}
        msgs,st2=N.plan([],[job('j0','done',NOW-50),job('j1','failed',NOW-10)],st,NOW)
        self.assertEqual(len(msgs),1);self.assertIn('j1',msgs[0]['title']);self.assertIn('failed',msgs[0]['title']);self.assertEqual(msgs[0]['priority'],4)
        self.assertEqual(N.plan([],[job('j1','failed',NOW-10)],st2,NOW)[0],[])
    def test_done_has_default_priority(self):
        msgs,_=N.plan([],[job('j2','done',NOW-5)],{'jobs_seen':[],'incidents_notified':{}},NOW);self.assertEqual(msgs[0]['priority'],3)
    def test_cap_per_run_and_overflow_summary(self):
        jobs=[job('j%d'%i,'done',NOW-i) for i in range(9)]
        msgs,st=N.plan([],jobs,{'jobs_seen':[],'incidents_notified':{}},NOW)
        self.assertEqual(len(msgs),N.MAX_PER_RUN);self.assertIn('weitere',msgs[-1]['title']);self.assertEqual(len(st['jobs_seen']),9)

class Safety(unittest.TestCase):
    def test_no_free_text_only_clean_ids(self):
        bad=inc('a',500,cls='X\x1b[31m'+'Y'*300,subj='sk-ant-abcdefghijklmnop1234\nZ')
        msgs,_=N.plan([bad],[],{'jobs_seen':[],'incidents_notified':{}},NOW)
        t=msgs[0]['title']+msgs[0]['message'];self.assertNotIn('\x1b',t);self.assertNotIn('\n',msgs[0]['title']);self.assertNotIn('abcdefghijklmnop1234',t);self.assertLess(len(t),400)
    def test_state_bounded(self):
        jobs=[job('j%d'%i,'done',NOW) for i in range(500)]
        _,st=N.plan([],jobs,{'jobs_seen':[],'incidents_notified':{}},NOW);self.assertLessEqual(len(st['jobs_seen']),N.SEEN_MAX)
    def test_corrupt_state_treated_as_first_run(self):
        msgs,st=N.plan([inc('a',500)],[],{'weird':1},NOW);self.assertEqual(msgs,[]);self.assertIn('jobs_seen',st)

if __name__=='__main__':unittest.main()
