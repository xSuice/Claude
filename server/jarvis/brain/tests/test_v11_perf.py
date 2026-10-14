"""V11 performance intelligence: fake /proc+/sys trees, retention, learned baseline, forecast,
hysteresis, adaptive polling, real CPU/IO stress and measured self-load in conserve mode."""
import json
import multiprocessing as mp
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from performance_intelligence import Collector, PerfIntel


def fake_tree(d: Path, *, mem_some=0.0, avail_kb=3_000_000, temp=None, battery=None, on_ac=True, power_uw=None,
              cpu_busy=False, io_full=0.0):
    p, s = d / 'proc', d / 'sys'
    (p / 'pressure').mkdir(parents=True, exist_ok=True)
    (p / 'pressure' / 'memory').write_text(f'some avg10={mem_some} avg60=0 avg300=0 total=0\nfull avg10=0.00 avg60=0 avg300=0 total=0\n')
    (p / 'pressure' / 'io').write_text(f'some avg10={io_full} avg60=0 avg300=0 total=0\nfull avg10={io_full} avg60=0 avg300=0 total=0\n')
    (p / 'pressure' / 'cpu').write_text('some avg10=0.00 avg60=0 avg300=0 total=0\n')
    (p / 'meminfo').write_text(f'MemTotal: 4000000 kB\nMemAvailable: {avail_kb} kB\nSwapTotal: 2000000 kB\nSwapFree: 1500000 kB\n')
    (p / 'loadavg').write_text('0.5 0.4 0.3 1/100 999\n')
    if temp is not None:
        z = s / 'class' / 'thermal' / 'thermal_zone0'; z.mkdir(parents=True, exist_ok=True)
        (z / 'temp').write_text(str(int(temp * 1000)))
    if battery is not None:
        b = s / 'class' / 'power_supply' / 'BAT0'; b.mkdir(parents=True, exist_ok=True)
        (b / 'type').write_text('Battery'); (b / 'capacity').write_text(str(battery))
        (b / 'status').write_text('Charging' if on_ac else 'Discharging')
        if power_uw is not None:
            (b / 'power_now').write_text(str(power_uw))
        a = s / 'class' / 'power_supply' / 'AC'; a.mkdir(parents=True, exist_ok=True)
        (a / 'type').write_text('Mains'); (a / 'online').write_text('1' if on_ac else '0')
    return p, s


class FakeTrees(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); self.d = Path(t.name)

    def pi(self, **kw):
        p, s = fake_tree(self.d, **kw)
        return PerfIntel(self.d / 'perf.db', Collector(p, s, disk_paths=[str(self.d)]))

    def test_missing_files_are_silent(self):
        empty = self.d / 'empty'; empty.mkdir()
        pi = PerfIntel(self.d / 'p.db', Collector(empty / 'proc', empty / 'sys', disk_paths=[str(empty / 'nope')]))
        for _ in range(3):
            r = pi.sample()
        self.assertEqual(r['mode'], 'normal'); self.assertEqual(pi.active(), [])
        self.assertTrue(set(r['metrics']) <= {'self_cpu_pct', 'self_rss_mb'})

    def test_memory_pressure_hysteresis_and_conserve(self):
        pi = self.pi(mem_some=30.0, avail_kb=200_000)
        r1 = pi.sample(1000); self.assertEqual(r1['mode'], 'normal')          # one sample is not enough
        r2 = pi.sample(1060); self.assertEqual(r2['changes'][0]['cond'], 'memory')
        self.assertEqual(r2['mode'], 'conserve'); self.assertIn('psi_mem_some', r2['changes'][0]['evidence'])
        fake_tree(self.d, mem_some=0.0, avail_kb=3_000_000)
        pi.sample(1120); pi.sample(1180); self.assertEqual(pi.mode(), 'conserve')  # no flapping
        r = pi.sample(1240); self.assertEqual(r['changes'], [{'cond': 'memory', 'kind': 'exit'}])
        self.assertEqual(pi.mode(), 'normal')

    def test_laptop_battery_and_thermal(self):
        pi = self.pi(battery=20, on_ac=False, power_uw=7_500_000)
        pi.sample(1); r = pi.sample(2)
        self.assertEqual(r['metrics']['power_w'], 7.5); self.assertTrue(r['metrics']['on_battery'])
        self.assertEqual(r['mode'], 'conserve')
        fake_tree(self.d, battery=8, on_ac=False); self.assertEqual(pi.sample(3)['mode'], 'protect')
        pi2 = PerfIntel(self.d / 'p2.db', Collector(*fake_tree(self.d / 'x', temp=95.0), disk_paths=[str(self.d)]))
        self.assertEqual(pi2.sample(1)['mode'], 'protect')
        self.assertEqual(pi2.sample(2)['metrics']['temp_c'], 95.0)

    def test_adaptive_interval(self):
        pi = self.pi()
        iv = [pi.sample(i * 100)['interval'] for i in range(8)]
        self.assertEqual(iv[-1], 300); self.assertTrue(iv == sorted(iv))
        fake_tree(self.d, mem_some=40.0)
        pi.sample(900); self.assertEqual(pi.sample(1000)['interval'], 30)

    def test_retention_downsampling_and_daily(self):
        pi = self.pi()
        now = int(datetime(2026, 10, 14, 12).timestamp())
        with pi._conn() as c:
            for i in range(0, 4 * 86400, 600):
                c.execute('INSERT INTO perf_raw VALUES(?,?)', (now - 4 * 86400 + i, json.dumps({'cpu_busy_pct': 10.0 + i % 7})))
        r = pi.downsample(now)
        with pi._conn() as c:
            oldest = c.execute('SELECT MIN(ts) FROM perf_raw').fetchone()[0]
            hours = c.execute("SELECT COUNT(*) FROM perf_hourly WHERE metric='cpu_busy_pct'").fetchone()[0]
            days = c.execute("SELECT COUNT(*) FROM perf_daily WHERE metric='cpu_busy_pct'").fetchone()[0]
        self.assertGreaterEqual(oldest, now - 48 * 3600); self.assertGreater(r['deleted_raw'], 0)
        self.assertGreaterEqual(hours, 90); self.assertGreaterEqual(days, 3)
        pi.downsample(now)                          # idempotent
        with pi._conn() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM perf_hourly WHERE metric='cpu_busy_pct'").fetchone()[0], hours)

    def test_learned_normal_marks_unusual(self):
        pi = self.pi()
        now = int(datetime(2026, 10, 14, 3, 30).timestamp())
        with pi._conn() as c:
            for d in range(1, 9):
                h = int(datetime(2026, 10, 14 - d, 3).timestamp())
                c.execute('INSERT INTO perf_hourly VALUES(?,?,?,?,?,?,?)', (h, 'cpu_busy_pct', 60, 8 + d % 3, 5, 12, 11))
        self.assertEqual(pi.unusual({'cpu_busy_pct': 9.0}, now), [])
        u = pi.unusual({'cpu_busy_pct': 70.0}, now)
        self.assertEqual(u[0]['metric'], 'cpu_busy_pct'); self.assertGreater(u[0]['z'], 4)
        self.assertEqual(pi.unusual({'cpu_busy_pct': 70.0}, int(datetime(2026, 10, 14, 15).timestamp())), [])  # no history

    def test_disk_full_forecast(self):
        pi = self.pi()
        with pi._conn() as c:
            for i in range(10):
                c.execute('INSERT INTO perf_daily VALUES(?,?,?,?,?)', (f'2026-10-{i + 1:02d}', 'disk_free_pct', 30 - 2 * i, 0, 0))
        f = pi.disk_forecast()
        self.assertAlmostEqual(f['trend_pct_per_day'], -2.0, places=2)
        self.assertAlmostEqual(f['days_to_floor'], 3.5, places=1)


def _burn(sec):
    t = time.time()
    while time.time() - t < sec:
        pass


@unittest.skipUnless(os.path.exists('/proc/pressure/cpu'), 'needs PSI')
class RealStress(unittest.TestCase):
    """Artificial pressure on this machine (bounded to a few seconds)."""
    def test_cpu_stress_is_detected(self):
        with tempfile.TemporaryDirectory() as t:
            pi = PerfIntel(Path(t) / 'p.db', limits={'psi_cpu_some': 5.0})
            pi.sample(0)
            procs = [mp.Process(target=_burn, args=(14,)) for _ in range((os.cpu_count() or 1) * 3)]
            [p.start() for p in procs]
            try:
                seen = False
                for i in range(1, 14):
                    time.sleep(1)
                    r = pi.sample(i)
                    if 'cpu' in pi.active():
                        seen = True; break
            finally:
                [p.terminate() for p in procs]; [p.join() for p in procs]
            self.assertTrue(seen, r['metrics'])
            self.assertEqual(pi.mode(), 'conserve')
            self.assertGreater(r['metrics']['cpu_busy_pct'], 80)

    def test_io_stress_raises_io_metrics(self):
        with tempfile.TemporaryDirectory() as t:
            c = Collector(disk_paths=[t]); c.sample()
            f = Path(t) / 'blob'
            t0 = time.time()
            with open(f, 'wb') as fh:
                while time.time() - t0 < 3:
                    fh.write(os.urandom(1 << 20)); fh.flush(); os.fsync(fh.fileno())
            m = c.sample()
            self.assertGreater(m.get('disk_write_kbs', 0), 1000, m)


class SelfLoadInConserve(unittest.TestCase):
    def test_daemon_does_less_work_in_conserve_mode(self):
        from brain_core import Brain
        from executive import Executive
        from daemon import Daemon
        cpu = {}
        for mode in ('normal', 'conserve'):
            with tempfile.TemporaryDirectory() as t:
                t = Path(t); (t / 'ws').mkdir()
                b = Brain(t / 'b.db', 'person-a', {'ma-home'})
                ex = Executive(b, {'actions': {'ok': {'argv': [sys.executable, '-c', 'pass']}}}, t / 'ws')
                sens = {'project': 'ma-home', 'sensors': [{'id': f's{i}', 'type': 'disk', 'path': str(t)} for i in range(8)]}
                lim = {'min_disk_percent': 101} if mode == 'conserve' else {}
                d = Daemon(b, 'ma-home', ex, sensors_cfg=sens, opts={'sensor_interval_seconds': 60, 'homeostasis': lim, 'sleep_hour': 99})
                now = int(time.time()); t0 = time.process_time()
                for i in range(120):
                    d.tick(now + 60 * i)
                cpu[mode] = time.process_time() - t0
                with b.connection() as db:
                    cpu[mode + '_scans'] = db.execute("SELECT ticks FROM daemon_state").fetchone()[0]
        self.assertLess(cpu['conserve'], cpu['normal'] * 0.8, cpu)


if __name__ == '__main__':
    unittest.main()
