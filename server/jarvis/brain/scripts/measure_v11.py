#!/usr/bin/env python3
"""V11 phase G: reproducible measurements, offline, no model calls.

  overhead RUNTIME_DIR [--perf]   CPU ms per daemon tick and peak RSS (run once per runtime/mode)
  sensors                         real CPU of sensor rounds per hour at interval 300 s vs 600 s
                                  (= the effect of the autopilot measure slow_sensors)
  chain                           order chain scenarios: V10.1 path (Claude queue) vs V11 path
                                  (permitted helper) - Claude jobs, helper calls, ticks
Helpers are a fake OpenAI-compatible server on 127.0.0.1; nothing leaves the machine.
"""
import json
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def overhead(runtime: Path, with_perf: bool, ticks=200):
    sys.path.insert(0, str(runtime))
    from brain_core import Brain
    from executive import Executive
    from daemon import Daemon
    d = Path(tempfile.mkdtemp()); (d / 'ws').mkdir()
    b = Brain(d / 'b.db', 'person-a', {'ma-home'})
    ex = Executive(b, {'actions': {'ok': {'argv': ['/bin/true']}}}, d / 'ws')
    kw = {}
    if with_perf:
        from performance_intelligence import PerfIntel, Collector
        kw['perf'] = PerfIntel(d / 'perf.db', Collector(disk_paths=['/']))
    dmn = Daemon(b, 'ma-home', ex, opts={'sensor_interval_seconds': 300}, **kw)
    now = int(time.time())
    dmn.tick(now)  # warm-up (schema creation)
    t0 = time.process_time()
    for i in range(ticks):
        now += 300  # every tick is a sampling tick for PI (worst case)
        dmn.tick(now)
    cpu_ms = (time.process_time() - t0) * 1000 / ticks
    return {'runtime': runtime.name if runtime.name != 'brain-runtime' else runtime.parent.name, 'perf': with_perf,
            'cpu_ms_per_tick': round(cpu_ms, 2), 'peak_rss_mb': round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)}


def sensors():
    """Real sensor subprocesses over one simulated hour, tick=60 s."""
    sys.path.insert(0, str(HERE))
    from brain_core import Brain
    from executive import Executive
    from daemon import Daemon
    out = {}
    for interval in (300, 600):
        d = Path(tempfile.mkdtemp()); (d / 'ws').mkdir()
        b = Brain(d / 'b.db', 'person-a', {'ma-home'})
        ex = Executive(b, {'actions': {}}, d / 'ws')
        cfg = {'project': 'ma-home', 'sensors': [{'id': f's{i}', 'type': 'systemd', 'unit': f'u{i}.service', 'severity': 3}
                                                 for i in range(4)]}
        def real(argv, timeout=10):
            p = subprocess.run([sys.executable, '-c', 'print("active")'], capture_output=True, text=True, timeout=timeout)
            return p.returncode, p.stdout.strip()
        dmn = Daemon(b, 'ma-home', ex, sensors_cfg=cfg, sensor_runner=real, opts={'sensor_interval_seconds': interval})
        now = 1_800_000_000
        c0 = resource.getrusage(resource.RUSAGE_CHILDREN); s0 = time.process_time()
        for _ in range(60):
            now += 60; dmn.tick(now)
        c1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        out[interval] = round((c1.ru_utime + c1.ru_stime - c0.ru_utime - c0.ru_stime + time.process_time() - s0) * 1000)
    return {'cpu_ms_per_hour_interval_300': out[300], 'cpu_ms_per_hour_interval_600': out[600],
            'reduction_pct': round(100 * (1 - out[600] / out[300]), 1)}


def chain():
    import unittest
    sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / 'tests'))
    import test_v11_providers as tp
    from test_v11_autopilot_chain import ChainBase
    res = {}

    class M(ChainBase):
        def runTest(self):
            for name, helper, autonomy, mode, cls in [
                    ('unknown failure, V10.1 path (Claude queue)', False, True, 'ok', 'internal'),
                    ('unknown failure, V11 helper permitted', True, True, 'ok', 'internal'),
                    ('helper outage -> Claude queue', True, True, '500', 'internal'),
                    ('private data, helper not permitted', True, True, 'ok', 'private')]:
                self.tearDown_dirs()
                tp.Fake.mode, tp.Fake.hits = mode, 0
                d = self.world(helper=helper, autonomy=autonomy)
                d.sensors_cfg['sensors'][0]['data_class'] = cls
                d.tick(); (self.ws / 'web.state').write_text('failed')
                t0 = time.perf_counter(); ticks = 0
                for _ in range(4):
                    d.tick(); ticks += 1
                    with self.b.connection() as db:
                        st = db.execute('SELECT status FROM steps').fetchone()
                    if (st and st[0] == 'verified') or self.jobs():
                        break
                res[name] = {'claude_jobs': self.jobs(), 'helper_calls': len(self.calls()),
                             'helper_http_hits': tp.Fake.hits, 'resolved_locally': bool(st and st[0] == 'verified'),
                             'ticks': ticks, 'wall_ms': round((time.perf_counter() - t0) * 1000), 'errors': d._state()['errors']}

        def tearDown_dirs(self):
            import shutil
            for p in self.d.iterdir():
                if p.name != 'fake.key':
                    shutil.rmtree(p) if p.is_dir() else p.unlink()

    tp.Base.setUpClass.__func__(M)
    try:
        r = unittest.TextTestRunner(stream=open('/dev/null', 'w')).run(M())
        if not r.wasSuccessful():
            raise SystemExit(str(r.errors or r.failures))
    finally:
        tp.Base.tearDownClass.__func__(M)
    return res


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'overhead':
        print(json.dumps(overhead(Path(sys.argv[2]).resolve(), '--perf' in sys.argv)))
    elif cmd == 'sensors':
        print(json.dumps(sensors()))
    else:
        print(json.dumps(chain(), indent=1, ensure_ascii=False))
