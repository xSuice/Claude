import json,sys,unittest,pathlib,tempfile,os,time
sys.path.insert(0,str(pathlib.Path(__file__).parent))
import telemetry_core as T

class Redact(unittest.TestCase):
    def test_secret_shapes_removed(self):
        for raw in ['key sk-ant-abcdefghijklmnop1234','Authorization: Bearer abc.def-123456789','password=hunter2 x','token: "abcd1234efgh5678"','https://user:pw@example.org/x','X-MA-Key: 0123456789abcdef0123456789abcdef']:
            out=T.redact(raw)
            for bad in ('abcdefghijklmnop1234','abc.def-123456789','hunter2','abcd1234efgh5678','user:pw','0123456789abcdef0123456789abcdef'):
                self.assertNotIn(bad,out,raw)
    def test_truncates_and_strips_control(self):
        out=T.redact('a\x1b[31m'+'x'*500+'\nline2',limit=100)
        self.assertLessEqual(len(out),101);self.assertNotIn('\x1b',out);self.assertNotIn('\n',out)

class Validate(unittest.TestCase):
    good={'cpu_pct':12.5,'ram_pct':60,'gpu':{'util_pct':3,'temp_c':45,'vram_used_mb':900,'vram_total_mb':6144}}
    def test_accepts_exact_schema(self):
        v=T.validate_pc(dict(self.good));self.assertEqual(v['cpu_pct'],12.5);self.assertEqual(v['gpu']['vram_total_mb'],6144)
    def test_gpu_optional(self):
        d=dict(self.good);del d['gpu'];self.assertIsNone(T.validate_pc(d)['gpu'])
    def test_rejects_unknown_fields_and_ranges(self):
        for bad in ({**self.good,'proc':'steam.exe'},{**self.good,'cpu_pct':101},{**self.good,'ram_pct':-1},{**self.good,'cpu_pct':'12'},{**self.good,'cpu_pct':float('nan')},{**self.good,'gpu':{'util_pct':1}},{**self.good,'gpu':{**self.good['gpu'],'x':1}},[1]):
            with self.assertRaises(ValueError,msg=str(bad)):T.validate_pc(bad)

class Store(unittest.TestCase):
    def test_write_read_age_and_stale(self):
        with tempfile.TemporaryDirectory() as d:
            p=os.path.join(d,'pc.json')
            self.assertEqual(T.read_pc(p,now=1000)['state'],'missing')
            T.write_pc(p,T.validate_pc(dict(Validate.good)),now=1000)
            r=T.read_pc(p,now=1060);self.assertEqual(r['state'],'fresh');self.assertEqual(r['age_s'],60)
            self.assertEqual(T.read_pc(p,now=1500)['state'],'stale')
            open(p,'w').write('{broken');self.assertEqual(T.read_pc(p,now=1000)['state'],'invalid')
    def test_file_mode_private(self):
        with tempfile.TemporaryDirectory() as d:
            p=os.path.join(d,'pc.json');T.write_pc(p,T.validate_pc(dict(Validate.good)),now=1)
            if os.name=='posix':self.assertEqual(os.stat(p).st_mode&0o077,0)

class Journal(unittest.TestCase):
    def test_summary_counts_and_redacts(self):
        lines=[json.dumps({'MESSAGE':'boom Bearer abcdefghij123456','__REALTIME_TIMESTAMP':str(i*10**6),'PRIORITY':'3'}) for i in range(1,6)]
        s=T.summarize_journal('\n'.join(lines))
        self.assertEqual(s['errors'],5);self.assertEqual(len(s['last']),3);self.assertNotIn('abcdefghij123456',json.dumps(s))
        self.assertEqual(s['last'][0]['t'],5)
    def test_ignores_garbage_lines(self):
        self.assertEqual(T.summarize_journal('not json\n{"MESSAGE":1}\n')['errors'],0)
    def test_units_whitelist_only(self):
        self.assertEqual(T.safe_units(['ma-home-web','x;rm -rf /','../etc','jarvis-watchdog']),['ma-home-web','jarvis-watchdog'])


class Council(unittest.TestCase):
    good={'cpu_pct':1,'ram_pct':1,'gpu':None,'council':{'window_h':24,'dms':30,'chains':8,'longest':17,'over_6':2}}
    def test_council_optional_and_accepted(self):
        v=T.validate_pc(dict(self.good));self.assertEqual(v['council']['longest'],17)
        d=dict(self.good);del d['council'];self.assertIsNone(T.validate_pc(d)['council'])
    def test_council_rejects_bad_shapes(self):
        for bad in ({**self.good['council'],'agent':'x'},{**self.good['council'],'longest':-1},{**self.good['council'],'over_6':99999},{'window_h':24}):
            with self.assertRaises(ValueError,msg=str(bad)):T.validate_pc({**self.good,'council':bad})
    def test_over6_cannot_exceed_chains(self):
        with self.assertRaises(ValueError):T.validate_pc({**self.good,'council':{**self.good['council'],'over_6':9,'chains':8}})
    def test_roundtrip_keeps_council(self):
        with tempfile.TemporaryDirectory() as d:
            p=os.path.join(d,'pc.json');T.write_pc(p,T.validate_pc(dict(self.good)),now=1)
            self.assertEqual(T.read_pc(p,now=2)['council']['dms'],30)

if __name__=='__main__':unittest.main()
