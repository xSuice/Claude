"""B1-Erweiterung fuer jarvis_deepcheck: Dauerlast, Swap, stille earlyoom-Abbrueche. Wird an test_jarvis_deepcheck angehaengt."""
import os, sqlite3, tempfile, unittest
import jarvis_deepcheck as D

NOW = 2_000_000_000


class ResourceB1Tests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = os.path.join(self.dir, 'b.db')
        c = sqlite3.connect(self.db)
        c.execute('create table jobs (id, state, updated, lease_until)')
        c.execute('create table job_events (id integer primary key, job_id, ts, kind, text)')
        c.commit(); c.close()
        self.err = os.path.join(self.dir, 'tick.err')

    def f(self, **kw):
        return D.findings(now=NOW, db=self.db, tick_err=self.err, **kw)

    def test_normal_resources_quiet(self):
        self.assertEqual(self.f(mem_mb=900, disk_pct=70, load15=0.4, swap_used_pct=15, oom_kills=0), [])

    def test_sustained_load_flagged(self):
        r = self.f(load15=4.2)
        self.assertEqual(len(r), 1)
        self.assertIn('Dauerlast', r[0])

    def test_swap_pressure_flagged(self):
        r = self.f(swap_used_pct=85)
        self.assertEqual(len(r), 1)
        self.assertIn('Swap', r[0])

    def test_oom_kills_flagged(self):
        r = self.f(oom_kills=2)
        self.assertEqual(len(r), 1)
        self.assertIn('earlyoom', r[0])
        self.assertIn('2', r[0])

    def test_oom_counter_parses_journal(self):
        lines = ['sending SIGTERM when mem avail <=  5.00% and swap free <= 10.00%,',
                 'sending SIGKILL when mem avail <=  2.50% and swap free <=  5.00%',
                 'Okt 28 14:50 ma-server earlyoom[1]: mem avail: 1728 of 2301 MiB',
                 'Okt 28 15:01 ma-server earlyoom[1]: low memory! at or below SIGTERM limits',
                 'Okt 28 15:01 ma-server earlyoom[1]: sending SIGTERM to process 4242 uid 1000 "python3": badness 900',
                 'Okt 28 15:02 ma-server earlyoom[1]: sending SIGKILL to process 4243 uid 1000 "node": badness 950']
        self.assertEqual(D.count_oom_kills(lines), 2)

    def test_swap_used_pct_from_meminfo(self):
        self.assertEqual(D.swap_used_pct({'SwapTotal': 1000, 'SwapFree': 250}), 75)
        self.assertEqual(D.swap_used_pct({'SwapTotal': 0, 'SwapFree': 0}), 0)


if __name__ == '__main__':
    unittest.main()
