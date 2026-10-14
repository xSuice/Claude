#!/usr/bin/env python3
"""V11 performance autopilot - only the brain's OWN knobs, only from an operator-pinned allowlist.

States per run: observe -> hypothesize -> propose -> dry_run -> measure_before -> apply_if_authorized
-> measure_after -> verify -> retain_or_rollback -> learn.

* Allowlist file (JSON, owner-only) must match the SHA-256 pinned in daemon.json; otherwise the
  autopilot is disabled. It can only name measures implemented here, all reversible and limited to
  the brain itself: slower own sensor polling, slower own perf sampling, fewer executor steps per
  tick, pause of Claude/helper dispatch. Foreign services, OS, network, disks, DB schema or Docker
  are out of reach by construction.
* autorun=false (default): runs stop at 'awaiting_approval' after the dry run.
* Verify = target metric improved by >= min_gain AND no quality regression (daemon errors, new
  deviations, blocked steps). Otherwise rollback; no hypothesis is stored as experience.
* One run at a time, cooldown per measure after a rollback, daily cap, auto-revert of retained
  measures when the triggering condition has been clear for `revert_after_h`.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import statistics
import time
from pathlib import Path

MEASURES = {
    'slow_sensors':      {'knob': 'sensor_interval_seconds', 'op': 'mul', 'by': 2, 'max': 1800},
    'slow_perf_sampling': {'knob': 'perf_max_interval', 'op': 'mul', 'by': 2, 'max': 1800},
    'fewer_steps':       {'knob': 'max_steps_per_run', 'op': 'add', 'by': -1, 'min': 1},
    'pause_remote':      {'knob': 'defer_remote', 'op': 'set', 'to': True},
}
SCHEMA = '''CREATE TABLE IF NOT EXISTS autopilot_runs(id INTEGER PRIMARY KEY AUTOINCREMENT, measure TEXT NOT NULL,
    cond TEXT NOT NULL, state TEXT NOT NULL, metric TEXT NOT NULL, before REAL, after REAL, old_value TEXT,
    new_value TEXT, guard_before TEXT, guard_after TEXT, created INTEGER NOT NULL, applied INTEGER, decided INTEGER,
    outcome TEXT, clear_since INTEGER)'''
ACTIVE = ('proposed', 'awaiting_approval', 'measuring_after', 'retained')


def load_allowlist(path: Path, pinned_sha256: str) -> dict:
    path = Path(path).expanduser().resolve(strict=True)
    raw = path.read_bytes()
    if os.name == 'posix' and (path.stat().st_mode & 0o022 or path.stat().st_uid != os.getuid()):
        raise PermissionError('autopilot allowlist must be owned by this user and not group/world writable')
    if hashlib.sha256(raw).hexdigest() != pinned_sha256:
        raise PermissionError('autopilot allowlist does not match the pinned SHA-256 - autopilot disabled')
    d = json.loads(raw)
    for name, m in d.get('measures', {}).items():
        if name not in MEASURES:
            raise ValueError(f'unknown measure {name} (only built-in, self-only measures are possible)')
        if set(m) - {'targets', 'metric', 'min_gain', 'auto'}:
            raise ValueError(f'{name}: unknown keys')
    return d


class Autopilot:
    def __init__(self, daemon, allowlist: dict, autorun=False, window=5, cooldown_h=6, max_runs_per_day=4,
                 revert_after_h=24):
        self.d, self.allow, self.autorun = daemon, allowlist.get('measures', {}), bool(autorun)
        self.window, self.cooldown, self.max_day, self.revert_after = window, cooldown_h * 3600, max_runs_per_day, revert_after_h * 3600
        self.db = daemon.brain.db_path
        with self._c() as c:
            c.execute(SCHEMA)

    def _c(self):
        class _C:
            def __init__(s, p): s.c = sqlite3.connect(str(p)); s.c.row_factory = sqlite3.Row
            def __enter__(s): return s.c
            def __exit__(s, *e): s.c.commit(); s.c.close()
        return _C(self.db)

    # ---- knobs (the only things this module can change) ----
    def _get(self, knob):
        if knob == 'sensor_interval_seconds': return self.d.o['sensor_interval_seconds']
        if knob == 'perf_max_interval': return self.d.perf.max_i if self.d.perf else None
        if knob == 'max_steps_per_run': return self.d.ex.limits['max_steps_per_run']
        if knob == 'defer_remote': return bool(self.d.o.get('defer_remote_override', False))

    def _set(self, knob, v):
        if knob == 'sensor_interval_seconds': self.d.o['sensor_interval_seconds'] = int(v)
        elif knob == 'perf_max_interval' and self.d.perf: self.d.perf.max_i = int(v)
        elif knob == 'max_steps_per_run': self.d.ex.limits['max_steps_per_run'] = int(v)
        elif knob == 'defer_remote': self.d.o['defer_remote_override'] = bool(v)

    def _new_value(self, spec, old):
        if spec['op'] == 'mul': return min(spec['max'], old * spec['by'])
        if spec['op'] == 'add': return max(spec['min'], old + spec['by'])
        return spec['to']

    # ---- evidence ----
    def _metric(self, name, n, since=0):
        if not self.d.perf:
            return None
        with self.d.perf._conn() as c:
            rows = c.execute('SELECT data FROM perf_raw WHERE ts>? ORDER BY ts DESC LIMIT ?', (since, n)).fetchall()
        vals = [json.loads(r[0]).get(name) for r in rows]
        vals = [v for v in vals if isinstance(v, (int, float))]
        return (statistics.mean(vals), len(vals)) if vals else (None, 0)

    def _guard(self):
        """Quality indicators that must not get worse because of a measure."""
        st = self.d._state()
        with self.d.brain.connection() as db:
            open_dev = db.execute("SELECT COUNT(*) FROM cognitive_anomalies WHERE owner=? AND status='open'",
                                  (self.d.brain.identity,)).fetchone()[0]
            blocked = db.execute("SELECT COUNT(*) FROM steps s JOIN goals g ON g.id=s.goal_id WHERE g.owner=? AND s.status='blocked'",
                                 (self.d.brain.identity,)).fetchone()[0]
        return {'errors': st['errors'], 'open_deviations': open_dev, 'blocked_steps': blocked}

    def _active(self):
        with self._c() as c:
            r = c.execute(f"SELECT * FROM autopilot_runs WHERE state IN ({','.join('?' * len(ACTIVE))}) ORDER BY id DESC LIMIT 1",
                          ACTIVE).fetchone()
        return dict(r) if r else None

    def _upd(self, rid, **kw):
        with self._c() as c:
            c.execute('UPDATE autopilot_runs SET ' + ','.join(f'{k}=?' for k in kw) + ' WHERE id=?', (*kw.values(), rid))

    # ---- the state machine, one step per daemon tick ----
    def step(self, now: int) -> dict:
        run = self._active()
        conds = set(self.d.perf.active()) if self.d.perf else set()
        if run is None:
            return self._observe(now, conds)
        spec = MEASURES[run['measure']]
        if run['state'] == 'awaiting_approval':
            return {'state': 'awaiting_approval', 'run': run['id']}
        if run['state'] == 'measuring_after':
            after, n = self._metric(run['metric'], self.window, since=run['applied'])
            if n < self.window:
                return {'state': 'measuring_after', 'run': run['id'], 'samples': n}
            gain = (run['before'] - after) / run['before'] if run['before'] else 0
            g0, g1 = json.loads(run['guard_before']), self._guard()
            regress = g1['errors'] > g0['errors'] or g1['open_deviations'] > g0['open_deviations'] \
                or g1['blocked_steps'] > g0['blocked_steps']
            min_gain = self.allow[run['measure']].get('min_gain', 0.2)
            ok = gain >= min_gain and not regress
            if not ok:
                self._set(spec['knob'], json.loads(run['old_value']))
            outcome = 'retained' if ok else ('rolled_back: quality regression' if regress else f'rolled_back: gain {gain:.0%}')
            self._upd(run['id'], state='retained' if ok else 'rolled_back', after=after, guard_after=json.dumps(g1),
                      decided=now, outcome=outcome)
            ep = self.d.brain.episode(self.d.project, f"perf:{run['measure']}", f"{run['measure']} gegen {run['cond']}",
                                      'success' if ok else 'failure',
                                      f"{run['metric']} {run['before']:.2f} -> {after:.2f} ({gain:+.0%}); guard {g0}->{g1}")
            self.d.brain.verify_episode(ep['id'])  # measured by the system, not reported by a model
            self.d.notice('info' if ok else 'warning', f"Autopilot {run['measure']}: {outcome}", now)
            return {'state': 'retained' if ok else 'rolled_back', 'run': run['id'], 'gain': round(gain, 3)}
        if run['state'] == 'retained':
            if run['cond'] in conds:
                self._upd(run['id'], clear_since=None); return {'state': 'retained', 'run': run['id']}
            clear = run['clear_since'] or now
            if not run['clear_since']:
                self._upd(run['id'], clear_since=now)
            if now - clear >= self.revert_after:
                self._set(spec['knob'], json.loads(run['old_value']))
                self._upd(run['id'], state='reverted', outcome='condition clear: back to default', decided=now)
                return {'state': 'reverted', 'run': run['id']}
            return {'state': 'retained', 'run': run['id']}
        return {'state': run['state']}

    def _observe(self, now, conds):
        with self._c() as c:
            n_day = c.execute('SELECT COUNT(*) FROM autopilot_runs WHERE created>=?', (now - 86400,)).fetchone()[0]
        if n_day >= self.max_day:
            return {'state': 'idle', 'reason': 'daily cap'}
        for name, m in self.allow.items():                       # hypothesize: allowlisted measures for active conditions
            hit = [c_ for c_ in m.get('targets', []) if c_ in conds]
            if not hit:
                continue
            with self._c() as c:
                last = c.execute("SELECT decided FROM autopilot_runs WHERE measure=? AND state='rolled_back' "
                                 "ORDER BY id DESC LIMIT 1", (name,)).fetchone()
            if last and now - (last[0] or 0) < self.cooldown:
                continue
            spec, metric = MEASURES[name], m.get('metric', 'self_cpu_pct')
            old = self._get(spec['knob'])
            if old is None:
                continue
            new = self._new_value(spec, old)
            if new == old:
                continue                                        # dry run: nothing would change
            before, n = self._metric(metric, self.window)
            if n < self.window or not before:
                return {'state': 'observe', 'reason': 'not enough baseline samples'}
            guard = self._guard()
            with self._c() as c:
                rid = c.execute('INSERT INTO autopilot_runs(measure,cond,state,metric,before,old_value,new_value,guard_before,created) '
                                'VALUES(?,?,?,?,?,?,?,?,?)', (name, hit[0], 'proposed', metric, before, json.dumps(old),
                                                              json.dumps(new), json.dumps(guard), now)).lastrowid
            if not (self.autorun and m.get('auto')):
                self._upd(rid, state='awaiting_approval')
                self.d.notice('action', f"Autopilot schlägt {name} vor ({hit[0]}: {metric} Ø {before:.2f}); "
                                        f"{spec['knob']} {old} -> {new}. Freigabe: autopilot approve {rid}", now)
                return {'state': 'awaiting_approval', 'run': rid}
            return self._apply(rid, now)
        return {'state': 'idle'}

    def _apply(self, rid, now):
        with self._c() as c:
            r = dict(c.execute('SELECT * FROM autopilot_runs WHERE id=?', (rid,)).fetchone())
        self._set(MEASURES[r['measure']]['knob'], json.loads(r['new_value']))
        self._upd(rid, state='measuring_after', applied=now)
        self.d.notice('info', f"Autopilot {r['measure']} angewendet, messe Wirkung", now)
        return {'state': 'measuring_after', 'run': rid}

    def approve(self, rid, now=None) -> dict:
        now = now or int(time.time())
        with self._c() as c:
            r = c.execute("SELECT state FROM autopilot_runs WHERE id=?", (rid,)).fetchone()
        if not r or r[0] != 'awaiting_approval':
            raise ValueError('no run awaiting approval')
        return self._apply(rid, now)

    def history(self, limit=20) -> list[dict]:
        with self._c() as c:
            return [dict(r) for r in c.execute('SELECT id,measure,cond,state,metric,before,after,outcome,created,decided '
                                               'FROM autopilot_runs ORDER BY id DESC LIMIT ?', (limit,))]
