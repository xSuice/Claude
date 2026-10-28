import os, sqlite3, tempfile, unittest
import jarvis_deepcheck as D

NOW = 2_000_000_000


class DeepTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = os.path.join(self.dir, 'b.db')
        c = sqlite3.connect(self.db)
        c.execute('create table jobs (id, state, updated, lease_until)')
        c.execute('create table job_events (id integer primary key, job_id, ts, kind, text)')
        c.commit(); c.close()
        self.err = os.path.join(self.dir, 'tick.err')

    def add(self, jid, st, upd, lease=None, ev=None):
        c = sqlite3.connect(self.db)
        c.execute('insert into jobs values (?,?,?,?)', (jid, st, upd, lease))
        if ev:
            c.execute('insert into job_events (job_id, ts, kind) values (?,?,?)', (jid, ev, 'x'))
        c.commit(); c.close()

    def f(self, **kw):
        return D.findings(now=NOW, db=self.db, tick_err=self.err, **kw)

    def test_clean(self):
        self.add('a', 'done', NOW - 99999)
        self.add('b', 'running', NOW - 60)
        self.assertEqual(self.f(mem_mb=900, disk_pct=70), [])

    def test_stuck_running(self):
        self.add('h', 'running', NOW - 3600)
        self.assertIn('ohne Fortschritt seit 60 min', self.f()[0])

    def test_recent_event_counts_as_progress(self):
        self.add('h', 'running', NOW - 3600, ev=NOW - 120)
        self.assertEqual(self.f(), [])

    def test_legit_wait_not_flagged_until_24h(self):
        self.add('w', 'waiting_approval', NOW - 5 * 3600)
        self.assertEqual(self.f(), [])
        self.add('w2', 'waiting_pc', NOW - 30 * 3600)
        self.assertIn('wartet seit 30 h', self.f()[0])

    def test_expired_lease(self):
        self.add('l', 'running', NOW - 60, lease=NOW - 1200)
        self.assertIn('Lease', self.f()[0])

    def test_new_tick_errors_once(self):
        st = {}
        open(self.err, 'w').write('boom\n')
        self.assertIn('Tick-Fehler', self.f(state=st)[0])
        self.assertEqual(self.f(state=st), [])

    def test_resources(self):
        r = self.f(mem_mb=80, disk_pct=5)
        self.assertEqual(len(r), 2)


if __name__ == '__main__':
    unittest.main()
