#!/usr/bin/env python3
"""V11 performance intelligence for a weak laptop server - stdlib only, no extra daemon.

Collector  cheap reads of /proc (stat, meminfo, vmstat, diskstats, pressure/*) and /sys
           (thermal, hwmon, cpufreq, power_supply incl. battery power draw) plus the brain's
           own CPU/RSS. Missing files are simply absent metrics - never errors or warnings.
Store      one SQLite DB: raw samples kept 48 h, hourly aggregates 30 d, daily 400 d
           (min/mean/max/p95). Nothing grows without bound.
Baseline   learned normal per metric and hour of day (median + MAD over 14 days); a robust
           z-score marks *unusual* values. Static limits stay as safety floor.
Detector   bottleneck conditions with hysteresis (enter after 2, leave after 3 samples):
           cpu, memory, io, thermal, disk_space, battery, self_load. Cause hints are labelled
           as correlations with their evidence, never as proven causes.
Mode       normal / conserve / protect - consumed by the daemon to shed its own work.
Polling    adaptive: stable -> interval grows to max; any condition -> back to min.
"""
from __future__ import annotations

import json
import os
import resource
import sqlite3
import statistics
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

METRICS = ('cpu_busy_pct', 'iowait_pct', 'load1_per_cpu', 'mem_avail_pct', 'mem_avail_mb', 'swap_used_mb',
           'swap_in_ps', 'swap_out_ps', 'psi_cpu_some', 'psi_mem_some', 'psi_mem_full', 'psi_io_some', 'psi_io_full',
           'disk_util_pct', 'disk_read_kbs', 'disk_write_kbs', 'disk_free_pct', 'inode_free_pct', 'temp_c',
           'cpu_freq_ratio', 'battery_pct', 'power_w', 'self_cpu_pct', 'self_rss_mb')
LIMITS = {'psi_cpu_some': 25.0, 'load1_per_cpu': 1.5, 'psi_mem_some': 10.0, 'mem_avail_pct': 10.0,
          'swap_in_ps': 50.0, 'psi_io_full': 10.0, 'disk_util_pct': 85.0, 'iowait_pct': 25.0, 'temp_c': 85.0,
          'temp_protect_c': 92.0, 'freq_ratio': 0.6, 'disk_free_pct': 10.0, 'disk_protect_pct': 5.0,
          'inode_free_pct': 10.0, 'battery_pct': 25.0, 'battery_protect_pct': 10.0, 'self_cpu_pct': 15.0}
CONSERVE = {'cpu', 'memory', 'io', 'thermal', 'disk_space', 'battery'}
SCHEMA = '''
CREATE TABLE IF NOT EXISTS perf_raw(ts INTEGER PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS perf_hourly(hour INTEGER NOT NULL, metric TEXT NOT NULL, n INTEGER, mean REAL,
    min REAL, max REAL, p95 REAL, PRIMARY KEY(hour, metric));
CREATE TABLE IF NOT EXISTS perf_daily(day TEXT NOT NULL, metric TEXT NOT NULL, mean REAL, max REAL, p95 REAL,
    PRIMARY KEY(day, metric));
CREATE TABLE IF NOT EXISTS perf_state(cond TEXT PRIMARY KEY, active INTEGER NOT NULL DEFAULT 0,
    streak_true INTEGER NOT NULL DEFAULT 0, streak_false INTEGER NOT NULL DEFAULT 0, since INTEGER);
CREATE TABLE IF NOT EXISTS perf_events(id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL,
    cond TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('enter','exit')), evidence TEXT);
CREATE TABLE IF NOT EXISTS perf_meta(k TEXT PRIMARY KEY, v TEXT);
'''


def _read(path):
    try:
        with open(path) as fh:
            return fh.read()
    except OSError:
        return None


def _num(path, scale=1.0):
    t = _read(path)
    try:
        return float(t.strip()) * scale if t else None
    except ValueError:
        return None


class Collector:
    """Stateful: rates need the previous sample. Everything optional."""
    def __init__(self, proc='/proc', sys='/sys', disk_paths=('/',), clock=time.monotonic):
        self.proc, self.sys, self.disk_paths, self.clock = Path(proc), Path(sys), list(disk_paths), clock
        self.prev = None

    def _cpu(self):
        t = _read(self.proc / 'stat')
        if not t:
            return None
        f = [int(x) for x in t.splitlines()[0].split()[1:]]
        idle, iow = f[3], f[4] if len(f) > 4 else 0
        return sum(f), idle, iow

    def _disk(self):
        t = _read(self.proc / 'diskstats')
        if not t:
            return None
        ticks, rd, wr = {}, 0, 0
        for line in t.splitlines():
            p = line.split()
            if len(p) < 14:
                continue
            name = p[2]
            if name.startswith(('loop', 'ram', 'zram', 'dm-', 'sr', 'fd')) or name[-1:].isdigit() and not name.startswith('nvme') and not name.startswith('mmcblk'):
                continue  # whole disks only (sda, nvme0n1, mmcblk0); partitions would double count
            if (name.startswith(('nvme', 'mmcblk')) and 'p' in name[-3:]):
                continue
            ticks[name] = int(p[12]); rd += int(p[5]); wr += int(p[9])
        return ticks, rd, wr

    def _psi(self, res):
        t = _read(self.proc / 'pressure' / res)
        out = {}
        if t:
            for line in t.splitlines():
                kind, *kv = line.split()
                for x in kv:
                    k, v = x.split('=')
                    if k == 'avg10':
                        out[kind] = float(v)
        return out

    def procs(self) -> dict:
        """Read-only process table: pid -> (comm, cpu ticks, rss MB). Only names, never arguments or environment."""
        out, page = {}, (os.sysconf('SC_PAGE_SIZE') if hasattr(os, 'sysconf') else 4096) / 1048576
        try:
            pids = [d.name for d in self.proc.iterdir() if d.name.isdigit()]
        except OSError:
            return out
        for pid in pids:
            t = _read(self.proc / pid / 'stat')
            if not t or ')' not in t:
                continue
            comm, rest = t[t.find('(') + 1:t.rfind(')')], t[t.rfind(')') + 2:].split()
            try:
                out[int(pid)] = (comm[:32], int(rest[11]) + int(rest[12]), round(int(rest[21]) * page, 1))
            except (IndexError, ValueError):
                continue
        return out

    def top(self, prev: dict | None, cur: dict, dt: float, n=5) -> dict:
        """Top consumers by CPU (needs a previous snapshot) and by RSS, grouped by process name."""
        hz = os.sysconf('SC_CLK_TCK') if hasattr(os, 'sysconf') else 100
        cpu, mem = {}, {}
        for pid, (comm, ticks, rss) in cur.items():
            mem[comm] = mem.get(comm, 0) + rss
            if prev and pid in prev and prev[pid][0] == comm and dt > 0:
                cpu[comm] = cpu.get(comm, 0) + max(0, ticks - prev[pid][1]) / hz / dt * 100
        best = lambda d: [{'name': k, 'value': round(v, 1)} for k, v in sorted(d.items(), key=lambda x: -x[1])[:n] if v > 0]  # noqa: E731
        return {'cpu_pct': best(cpu), 'rss_mb': best(mem)}

    def _self(self):
        a, b = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
        return a.ru_utime + a.ru_stime + b.ru_utime + b.ru_stime

    def sample(self) -> dict:
        now, m = self.clock(), {}
        cpu, disk, vm = self._cpu(), self._disk(), _read(self.proc / 'vmstat')
        swin = swout = None
        if vm:
            d = dict(l.split() for l in vm.splitlines() if len(l.split()) == 2)
            swin, swout = int(d.get('pswpin', 0)), int(d.get('pswpout', 0))
        cur = {'t': now, 'cpu': cpu, 'disk': disk, 'swin': swin, 'swout': swout, 'self': self._self()}
        ncpu = os.cpu_count() or 1
        if self.prev:
            dt = max(now - self.prev['t'], 1e-6)
            if cpu and self.prev['cpu']:
                tot = cpu[0] - self.prev['cpu'][0] or 1
                m['cpu_busy_pct'] = round(100 * (1 - (cpu[1] - self.prev['cpu'][1]) / tot), 1)
                m['iowait_pct'] = round(100 * (cpu[2] - self.prev['cpu'][2]) / tot, 1)
            if disk and self.prev['disk']:
                util = [(disk[0][k] - self.prev['disk'][0].get(k, disk[0][k])) / (dt * 1000) * 100 for k in disk[0]]
                if util:
                    m['disk_util_pct'] = round(min(100.0, max(util)), 1)
                m['disk_read_kbs'] = round((disk[1] - self.prev['disk'][1]) * 0.5 / dt, 1)
                m['disk_write_kbs'] = round((disk[2] - self.prev['disk'][2]) * 0.5 / dt, 1)
            if swin is not None and self.prev['swin'] is not None:
                m['swap_in_ps'] = round((swin - self.prev['swin']) / dt, 2)
                m['swap_out_ps'] = round((swout - self.prev['swout']) / dt, 2)
            if dt >= 5:  # rates over tiny windows are noise, not load
                m['self_cpu_pct'] = round(100 * (cur['self'] - self.prev['self']) / dt / ncpu, 2)
        self.prev = cur
        la = _read(self.proc / 'loadavg')
        if la:
            m['load1_per_cpu'] = round(float(la.split()[0]) / ncpu, 2)
        mi = _read(self.proc / 'meminfo')
        if mi:
            d = {l.split(':')[0]: int(l.split()[1]) for l in mi.splitlines() if len(l.split()) >= 2}
            if d.get('MemTotal'):
                m['mem_avail_mb'] = d.get('MemAvailable', 0) // 1024
                m['mem_avail_pct'] = round(100 * d.get('MemAvailable', 0) / d['MemTotal'], 1)
                m['swap_used_mb'] = (d.get('SwapTotal', 0) - d.get('SwapFree', 0)) // 1024
        for res, key in (('cpu', 'cpu'), ('memory', 'mem'), ('io', 'io')):
            p = self._psi(res)
            if 'some' in p:
                m[f'psi_{key}_some'] = p['some']
            if 'full' in p and res != 'cpu':
                m[f'psi_{key}_full'] = p['full']
        free = inode = None
        for path in self.disk_paths:
            try:
                s = os.statvfs(path)
            except OSError:
                continue
            if s.f_blocks:
                f = 100 * s.f_bavail / s.f_blocks
                free = f if free is None else min(free, f)
            if s.f_files:
                i = 100 * s.f_favail / s.f_files
                inode = i if inode is None else min(inode, i)
        if free is not None:
            m['disk_free_pct'] = round(free, 1)
        if inode is not None:
            m['inode_free_pct'] = round(inode, 1)
        temps = [_num(z / 'temp', 0.001) for z in (self.sys / 'class' / 'thermal').glob('thermal_zone*')]
        temps += [_num(t, 0.001) for t in (self.sys / 'class' / 'hwmon').glob('hwmon*/temp*_input')]
        temps = [t for t in temps if t is not None and 0 < t < 150]
        if temps:
            m['temp_c'] = round(max(temps), 1)
        ratios = []
        for c in (self.sys / 'devices' / 'system' / 'cpu').glob('cpu[0-9]*/cpufreq'):
            cur_f, max_f = _num(c / 'scaling_cur_freq'), _num(c / 'cpuinfo_max_freq')
            if cur_f and max_f:
                ratios.append(cur_f / max_f)
        if ratios:
            m['cpu_freq_ratio'] = round(sum(ratios) / len(ratios), 2)
        on_ac = None
        for ps in (self.sys / 'class' / 'power_supply').glob('*'):
            typ = (_read(ps / 'type') or '').strip()
            if typ == 'Mains':
                on_ac = (_read(ps / 'online') or '0').strip() == '1'
            elif typ == 'Battery':
                cap = _num(ps / 'capacity')
                if cap is not None:
                    m['battery_pct'] = cap
                pw = _num(ps / 'power_now', 1e-6)
                if pw is None:
                    c, v = _num(ps / 'current_now', 1e-6), _num(ps / 'voltage_now', 1e-6)
                    pw = c * v if c is not None and v is not None else None
                if pw is not None:
                    m['power_w'] = round(pw, 2)  # battery discharge/charge power: the laptop's energy draw
                st = (_read(ps / 'status') or '').strip()
                if st == 'Discharging':
                    on_ac = False if on_ac is None else on_ac
        if on_ac is not None:
            m['on_battery'] = not on_ac
        st = _read(self.proc / 'self' / 'status')
        if st:
            for line in st.splitlines():
                if line.startswith('VmRSS:'):
                    m['self_rss_mb'] = round(int(line.split()[1]) / 1024, 1)
        return m


class PerfIntel:
    def __init__(self, db: Path, collector: Collector | None = None, limits: dict | None = None,
                 min_interval=30, max_interval=300):
        self.db = Path(db)
        self.c = collector or Collector()
        self.lim = {**LIMITS, **(limits or {})}
        self.min_i, self.max_i = min_interval, max_interval
        new = not self.db.exists()
        self.db.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)
        if new and os.name == 'posix':
            try: os.chmod(self.db, 0o600)
            except OSError: pass
        self.last = None
        self._next = None  # cached next_sample (due() runs every tick)
        self._procs = None  # previous process snapshot, kept ONLY while cpu/memory pressure is seen
        self.top = None

    @contextmanager
    def _conn(self):
        # V11 laptop tuning: re-entrant, so one sample = one connection + one commit (was 8 fsyncs)
        if getattr(self, '_cx', None) is not None:
            yield self._cx; return
        c = sqlite3.connect(str(self.db), timeout=5)
        c.row_factory = sqlite3.Row
        self._cx = c
        try:
            yield c
            c.commit()
        finally:
            self._cx = None
            c.close()

    def _meta(self, k, default=None):
        with self._conn() as c:
            r = c.execute('SELECT v FROM perf_meta WHERE k=?', (k,)).fetchone()
        return json.loads(r[0]) if r else default

    def _set_meta(self, k, v):
        with self._conn() as c:
            c.execute('INSERT OR REPLACE INTO perf_meta VALUES(?,?)', (k, json.dumps(v)))

    # ---------- detection ----------
    def conditions(self, m: dict) -> dict:
        L, g = self.lim, m.get
        def gt(k, lim):
            return g(k) is not None and g(k) >= lim
        def lt(k, lim):
            return g(k) is not None and g(k) < lim
        cpu = gt('psi_cpu_some', L['psi_cpu_some']) or (g('psi_cpu_some') is None and gt('load1_per_cpu', L['load1_per_cpu']))
        return {
            'cpu': cpu,
            'memory': gt('psi_mem_some', L['psi_mem_some']) or lt('mem_avail_pct', L['mem_avail_pct']) or gt('swap_in_ps', L['swap_in_ps']),
            'io': gt('psi_io_full', L['psi_io_full']) or gt('disk_util_pct', L['disk_util_pct']) or gt('iowait_pct', L['iowait_pct']),
            'thermal': gt('temp_c', L['temp_c']) or (lt('cpu_freq_ratio', L['freq_ratio']) and gt('cpu_busy_pct', 50)),
            'disk_space': lt('disk_free_pct', L['disk_free_pct']) or lt('inode_free_pct', L['inode_free_pct']),
            'battery': bool(g('on_battery')) and lt('battery_pct', L['battery_pct']),
            'self_load': gt('self_cpu_pct', L['self_cpu_pct']),
        }

    def _hysteresis(self, conds: dict, m: dict, now: int, enter_n=2, exit_n=3) -> list[dict]:
        changes = []
        with self._conn() as c:
            for cond, val in conds.items():
                r = c.execute('SELECT * FROM perf_state WHERE cond=?', (cond,)).fetchone()
                act, st, sf, since = (r['active'], r['streak_true'], r['streak_false'], r['since']) if r else (0, 0, 0, None)
                st, sf = (st + 1, 0) if val else (0, sf + 1)
                if not act and st >= enter_n:
                    act, since = 1, now
                    ev = {k: m[k] for k in self._evidence_keys(cond) if k in m}
                    if cond in ('cpu', 'memory') and self.top:
                        ev['top'] = self.top['cpu_pct' if cond == 'cpu' else 'rss_mb']
                    ev = json.dumps(ev)
                    c.execute('INSERT INTO perf_events(ts,cond,kind,evidence) VALUES(?,?,?,?)', (now, cond, 'enter', ev))
                    changes.append({'cond': cond, 'kind': 'enter', 'evidence': json.loads(ev)})
                elif act and sf >= exit_n:
                    act = 0
                    c.execute('INSERT INTO perf_events(ts,cond,kind,evidence) VALUES(?,?,?,?)', (now, cond, 'exit', None))
                    changes.append({'cond': cond, 'kind': 'exit'})
                c.execute('INSERT OR REPLACE INTO perf_state VALUES(?,?,?,?,?)', (cond, act, st, sf, since))
        return changes

    @staticmethod
    def _evidence_keys(cond):
        return {'cpu': ('psi_cpu_some', 'load1_per_cpu', 'cpu_busy_pct'),
                'memory': ('psi_mem_some', 'psi_mem_full', 'mem_avail_pct', 'swap_in_ps', 'swap_used_mb'),
                'io': ('psi_io_some', 'psi_io_full', 'disk_util_pct', 'iowait_pct', 'disk_write_kbs'),
                'thermal': ('temp_c', 'cpu_freq_ratio', 'cpu_busy_pct'),
                'disk_space': ('disk_free_pct', 'inode_free_pct'),
                'battery': ('battery_pct', 'power_w'), 'self_load': ('self_cpu_pct', 'self_rss_mb')}[cond]

    def active(self) -> list[str]:
        with self._conn() as c:
            return [r[0] for r in c.execute('SELECT cond FROM perf_state WHERE active=1 ORDER BY cond')]

    def mode(self, m: dict | None = None) -> str:
        m = m or self.last or {}
        act = set(self.active())
        L = self.lim
        if (m.get('temp_c') or 0) >= L['temp_protect_c'] or (m.get('disk_free_pct') is not None and m['disk_free_pct'] < L['disk_protect_pct']) \
                or (m.get('on_battery') and (m.get('battery_pct') or 100) < L['battery_protect_pct']):
            return 'protect'
        return 'conserve' if act & CONSERVE else 'normal'

    def causes(self) -> list[dict]:
        """Correlation-based hints with evidence; explicitly not proven causes."""
        act, m, out = set(self.active()), self.last or {}, []
        if {'memory', 'io'} <= act and (m.get('swap_in_ps') or 0) + (m.get('swap_out_ps') or 0) > 0:
            out.append({'hint': 'Speicherdruck führt wahrscheinlich zu Swap-IO', 'evidence': {k: m.get(k) for k in
                        ('mem_avail_pct', 'swap_in_ps', 'swap_out_ps', 'psi_io_full')}, 'status': 'korreliert'})
        if 'thermal' in act and 'cpu' in act:
            out.append({'hint': 'Hohe Last bei Temperatur/Drosselung - Leistung durch Wärme begrenzt',
                        'evidence': {k: m.get(k) for k in ('temp_c', 'cpu_freq_ratio', 'cpu_busy_pct')}, 'status': 'korreliert'})
        if 'io' in act and 'memory' not in act:
            out.append({'hint': 'Datenträger ausgelastet (kein Speicherdruck erkennbar)',
                        'evidence': {k: m.get(k) for k in ('disk_util_pct', 'psi_io_full', 'disk_write_kbs')}, 'status': 'korreliert'})
        if self.top and ({'cpu', 'memory'} & act):
            t = self.top['cpu_pct'] if 'cpu' in act and self.top['cpu_pct'] else self.top['rss_mb']
            if t:
                out.append({'hint': f"Größter Verbraucher: {t[0]['name']}", 'evidence': {'top': t[:3]}, 'status': 'gemessen'})
        if 'self_load' in act:
            out.append({'hint': 'Eigenlast des Brains ist hoch', 'evidence': {k: m.get(k) for k in ('self_cpu_pct', 'self_rss_mb')},
                        'status': 'gemessen'})
        return out

    def unusual(self, m: dict, now: int, z=4.0) -> list[dict]:
        """Values far from the learned normal for this hour of day (needs >= 5 days of history)."""
        hour = datetime.fromtimestamp(now).hour
        out = []
        with self._conn() as c:
            for k in ('cpu_busy_pct', 'psi_cpu_some', 'psi_mem_some', 'psi_io_some', 'disk_util_pct', 'temp_c', 'power_w'):
                if m.get(k) is None:
                    continue
                vals = [r[0] for r in c.execute(
                    "SELECT mean FROM perf_hourly WHERE metric=? AND hour>=? AND CAST(strftime('%H', hour, 'unixepoch', 'localtime') AS INTEGER)=?",
                    (k, now - 14 * 86400, hour))]
                if len(vals) < 5:
                    continue
                med = statistics.median(vals)
                mad = statistics.median([abs(v - med) for v in vals]) * 1.4826 or max(0.5, abs(med) * 0.05)
                score = (m[k] - med) / mad
                if score >= z:
                    out.append({'metric': k, 'value': m[k], 'normal_median': round(med, 2), 'z': round(score, 1)})
        return out

    # ---------- sampling ----------
    def due(self, now: int) -> bool:
        if self._next is None:
            self._next = self._meta('next_sample', 0)
        return now >= self._next

    def sample(self, now: int | None = None) -> dict:
        now = int(time.time()) if now is None else now
        m = self.c.sample()
        self.last = m
        conds = self.conditions(m)
        if conds['cpu'] or conds['memory']:   # V11.1 root-cause evidence: who uses CPU/RAM? (read-only, only under pressure)
            snap, t = self.c.procs(), time.monotonic()
            prev = self._procs
            self.top = self.c.top(prev[1] if prev else None, snap, t - prev[0] if prev else 0)
            self._procs = (t, snap)
        else:
            self._procs, self.top = None, None
        with self._conn() as c:
            c.execute('INSERT OR REPLACE INTO perf_raw VALUES(?,?)', (now, json.dumps(m, separators=(',', ':'))))
            changes = self._hysteresis(conds, m, now)
            unusual = self.unusual(m, now)
            cur = self._meta('interval', self.min_i)
            busy = bool(self.active()) or bool(unusual) or bool(changes)
            interval = self.min_i if busy else min(self.max_i, int(cur * 1.5))
            self._set_meta('interval', interval); self._set_meta('next_sample', now + interval)
        self._next = now + interval
        return {'metrics': m, 'changes': changes, 'unusual': unusual, 'interval': interval, 'mode': self.mode(m)}

    # ---------- retention ----------
    def downsample(self, now: int | None = None) -> dict:
        now = int(time.time()) if now is None else now
        cur_hour = now - now % 3600
        made = 0
        with self._conn() as c:
            rows = c.execute('SELECT ts,data FROM perf_raw WHERE ts<? ORDER BY ts', (cur_hour,)).fetchall()
            buckets = {}
            for r in rows:
                h = r['ts'] - r['ts'] % 3600
                for k, v in json.loads(r['data']).items():
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        buckets.setdefault((h, k), []).append(float(v))
            for (h, k), vs in buckets.items():
                vs.sort()
                c.execute('INSERT OR REPLACE INTO perf_hourly VALUES(?,?,?,?,?,?,?)',
                          (h, k, len(vs), sum(vs) / len(vs), vs[0], vs[-1], vs[min(len(vs) - 1, int(0.95 * len(vs)))]))
                made += 1
            days = c.execute("SELECT DISTINCT date(hour,'unixepoch','localtime') FROM perf_hourly WHERE hour<?",
                             (now - now % 86400,)).fetchall()
            for (day,) in days:
                c.execute("INSERT OR REPLACE INTO perf_daily SELECT ?, metric, AVG(mean), MAX(max), MAX(p95) FROM perf_hourly "
                          "WHERE date(hour,'unixepoch','localtime')=? GROUP BY metric", (day, day))
            d_raw = c.execute('DELETE FROM perf_raw WHERE ts<?', (now - 48 * 3600,)).rowcount
            d_h = c.execute('DELETE FROM perf_hourly WHERE hour<?', (now - 30 * 86400,)).rowcount
            d_d = c.execute("DELETE FROM perf_daily WHERE day<date(?, 'unixepoch', '-400 days')", (now,)).rowcount
            c.execute('DELETE FROM perf_events WHERE ts<?', (now - 90 * 86400,))
        return {'hourly_rows': made, 'deleted_raw': d_raw, 'deleted_hourly': d_h, 'deleted_daily': d_d}

    # ---------- early warning ----------
    def disk_forecast(self, now: int | None = None, min_days=5) -> dict | None:
        """Linear trend of daily mean free space -> days until the protect floor (5 %)."""
        with self._conn() as c:
            rows = c.execute("SELECT day, mean FROM perf_daily WHERE metric='disk_free_pct' ORDER BY day DESC LIMIT 30").fetchall()
        if len(rows) < min_days:
            return None
        pts = [(datetime.fromisoformat(r['day']).timestamp() / 86400, r['mean']) for r in reversed(rows)]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        den = sum((x - mx) ** 2 for x in xs) or 1
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
        if slope >= -0.01:
            return {'trend_pct_per_day': round(slope, 3), 'days_to_floor': None}
        days = (ys[-1] - self.lim['disk_protect_pct']) / -slope
        return {'trend_pct_per_day': round(slope, 3), 'days_to_floor': round(days, 1), 'now_pct': ys[-1]}

    # ---------- reporting ----------
    def report(self, hours=24, now: int | None = None) -> dict:
        now = int(time.time()) if now is None else now
        with self._conn() as c:
            trend = {r['metric']: {'mean': round(r['mean'], 2), 'p95': round(r['p95'], 2), 'max': round(r['max'], 2)}
                     for r in c.execute('SELECT metric, AVG(mean) mean, MAX(p95) p95, MAX(max) max FROM perf_hourly '
                                        'WHERE hour>=? GROUP BY metric', (now - hours * 3600,))}
            top = [dict(r) for r in c.execute("SELECT cond, COUNT(*) episodes FROM perf_events WHERE kind='enter' AND ts>=? "
                                              "GROUP BY cond ORDER BY episodes DESC LIMIT 5", (now - hours * 3600,))]
            raw = c.execute('SELECT COUNT(*) FROM perf_raw').fetchone()[0]
            last = self.last
            if last is None:  # fresh process (CLI): newest stored sample instead of nothing
                r = c.execute('SELECT ts, data FROM perf_raw ORDER BY ts DESC LIMIT 1').fetchone()
                last = {**json.loads(r[1]), 'ts': r[0]} if r else None
        return {'mode': self.mode(), 'active': self.active(), 'last': last, 'causes': self.causes(), 'top_consumers': self.top,
                f'trend_{hours}h': trend, 'top_bottlenecks': top, 'disk_forecast': self.disk_forecast(now),
                'interval_s': self._meta('interval', self.min_i), 'raw_rows': raw,
                'note': 'Ursachen sind Korrelationen mit Evidenz, keine bewiesenen Kausalketten.'}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--db', type=Path, required=True)
    ap.add_argument('cmd', choices=['sample', 'report', 'downsample'])
    ap.add_argument('--hours', type=int, default=24)
    a = ap.parse_args()
    pi = PerfIntel(a.db)
    if a.cmd == 'sample':
        pi.c.sample(); time.sleep(1); out = pi.sample()
    elif a.cmd == 'downsample':
        out = pi.downsample()
    else:
        pi.last = pi.c.sample(); time.sleep(1); pi.last = pi.c.sample(); out = pi.report(a.hours)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
