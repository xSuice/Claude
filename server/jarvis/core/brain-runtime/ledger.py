"""V16 global budget ledger: ONE shared SQLite file for every identity, project and process.

Every model call (Claude worker, cloud helper) must first `reserve()` here. The check of all limits
and the insert happen in one BEGIN IMMEDIATE transaction, so parallel threads, several processes
and two users with physically separate brain databases still share one hard limit. After the call
`settle()` replaces the conservative estimate by the measured usage; a call whose usage is unknown
(timeout, crash) keeps its reservation as used. Reservations older than `stale_after_s` that were
never settled count as used (a crashed worker cannot free budget by dying).

Windows are rolling 24 h (time-zone independent). Units are kept apart on purpose:
  calls / tokens  - measured model usage (Claude CLI `usage`, helper `usage`)
  list_usd        - API list-price equivalent reported by the Claude CLI; NOT a bill. With a
                    Claude Pro/Max plan nothing is billed per call; the real plan quota is only
                    visible as percentage through the bridge (`plan_guard`).
"""
from __future__ import annotations

import json
import socket
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

SCHEMA = '''
CREATE TABLE IF NOT EXISTS reservations(
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, identity TEXT NOT NULL, project TEXT NOT NULL,
    job_id TEXT, resource TEXT NOT NULL, tokens_reserved INTEGER NOT NULL,
    tokens_used INTEGER, list_usd REAL, state TEXT NOT NULL CHECK(state IN ('reserved','settled','released')),
    settled INTEGER, note TEXT);
CREATE INDEX IF NOT EXISTS reservations_res_ts ON reservations(resource, ts);
CREATE INDEX IF NOT EXISTS reservations_id_ts ON reservations(identity, ts);
'''
DAY = 86400
DEFAULT_LIMITS = {
    'claude': {'calls_per_day': 40, 'tokens_per_day': 1_500_000, 'identity_calls_per_day': 30, 'max_concurrent': 1},
    'helper': {'calls_per_day': 30, 'tokens_per_day': 150_000, 'identity_calls_per_day': 30, 'max_concurrent': 2},
    'stale_after_s': 3600,
    'plan_guard': {'five_hour_max_pct': 70, 'week_max_pct': 85, 'fail_closed': False},
}


def merge_limits(cfg: dict | None) -> dict:
    out = json.loads(json.dumps(DEFAULT_LIMITS))
    for k, v in (cfg or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    for kind in ('claude', 'helper'):
        for key, val in out[kind].items():
            if type(val) is not int or val < 0:
                raise ValueError(f'limit {kind}.{key} must be an integer >= 0')
    return out


class Ledger:
    def __init__(self, db: Path, limits: dict | None = None, clock=time.time, plan_probe=None):
        self.db = Path(db).expanduser()
        self.db.parent.mkdir(parents=True, exist_ok=True)
        if not self.db.exists():
            self.db.touch(mode=0o600)
        self.limits = merge_limits(limits)
        self.clock = clock
        self.plan_probe = plan_probe  # callable -> {'five': {'p': %}, 'week': {'p': %}} or None
        with self._conn(True) as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self, write=False):
        c = sqlite3.connect(str(self.db), timeout=30)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA busy_timeout = 30000')
        try:
            if write:
                c.execute('BEGIN IMMEDIATE')
            yield c
            if write:
                c.commit()
        except Exception:
            if write:
                c.rollback()
            raise
        finally:
            c.close()

    @staticmethod
    def kind(resource: str) -> str:
        return 'claude' if resource == 'claude' or resource.startswith('claude:') else 'helper'

    def _used(self, c, where: str, args: tuple, now: int) -> tuple[int, int]:
        r = c.execute(f"SELECT COUNT(*), COALESCE(SUM(CASE WHEN state='settled' THEN COALESCE(tokens_used, tokens_reserved) "
                      f"ELSE tokens_reserved END),0) FROM reservations WHERE state!='released' AND ts>=? AND {where}",
                      (now - DAY, *args)).fetchone()
        return int(r[0]), int(r[1])

    def plan_check(self) -> str | None:
        """Real plan quota (percent) from the bridge. None = fine or unknown (unless fail_closed)."""
        g = self.limits.get('plan_guard') or {}
        if not self.plan_probe:
            return None
        try:
            p = self.plan_probe()
        except Exception:  # noqa: BLE001 - probe failures must not crash the scheduler
            p = None
        if not p or not p.get('ok', True):
            return 'plan usage unknown' if g.get('fail_closed') else None
        five = (p.get('five') or {}).get('p')
        week = (p.get('week') or {}).get('p')
        if isinstance(five, (int, float)) and five >= g.get('five_hour_max_pct', 101):
            return f'plan 5h window at {five}% (limit {g["five_hour_max_pct"]}%)'
        if isinstance(week, (int, float)) and week >= g.get('week_max_pct', 101):
            return f'plan week at {week}% (limit {g["week_max_pct"]}%)'
        return None

    def reserve(self, identity: str, project: str, resource: str, tokens: int, job_id: str | None = None,
                check_plan: bool = True) -> tuple[int | None, str]:
        """Returns (reservation_id, '') or (None, reason). Atomic over all processes."""
        if type(tokens) is not int or tokens < 0:
            raise ValueError('tokens must be int >= 0')
        kind = self.kind(resource)
        lim = self.limits[kind]
        if kind == 'claude' and check_plan:
            why = self.plan_check()
            if why:
                return None, why
        now = int(self.clock())
        with self._conn(True) as c:
            stale = now - int(self.limits['stale_after_s'])
            like = 'claude%' if kind == 'claude' else 'helper%'
            calls, toks = self._used(c, 'resource LIKE ?', (like,), now)
            if calls + 1 > lim['calls_per_day']:
                return None, f'global daily {kind} call limit {lim["calls_per_day"]} reached'
            if toks + tokens > lim['tokens_per_day']:
                return None, f'global daily {kind} token limit {lim["tokens_per_day"]} reached'
            icalls, _ = self._used(c, 'resource LIKE ? AND identity=?', (like, identity), now)
            if icalls + 1 > lim['identity_calls_per_day']:
                return None, f'daily {kind} call limit for {identity} reached'
            running = c.execute("SELECT COUNT(*) FROM reservations WHERE state='reserved' AND resource LIKE ? AND ts>=?",
                                (like, stale)).fetchone()[0]
            if running + 1 > lim['max_concurrent']:
                return None, f'{kind} concurrency limit {lim["max_concurrent"]} reached'
            cur = c.execute('INSERT INTO reservations(ts,identity,project,job_id,resource,tokens_reserved,state) '
                            "VALUES(?,?,?,?,?,?,'reserved')", (now, identity, project, job_id, resource, tokens))
            return int(cur.lastrowid), ''

    def settle(self, rid: int, tokens_used: int | None, list_usd: float | None = None, note: str = '') -> None:
        with self._conn(True) as c:
            c.execute("UPDATE reservations SET state='settled', tokens_used=?, list_usd=?, settled=?, note=? "
                      "WHERE id=? AND state='reserved'", (tokens_used, list_usd, int(self.clock()), note[:200], rid))

    def release(self, rid: int, note: str = 'not sent') -> None:
        """Only for calls that provably never reached a model (e.g. the program did not start)."""
        with self._conn(True) as c:
            c.execute("UPDATE reservations SET state='released', settled=?, note=? WHERE id=? AND state='reserved'",
                      (int(self.clock()), note[:200], rid))

    def usage(self, identity: str | None = None) -> dict:
        now = int(self.clock())
        out = {}
        with self._conn() as c:
            for kind in ('claude', 'helper'):
                like = kind + '%'
                calls, toks = self._used(c, 'resource LIKE ?', (like,), now)
                row = {'calls_24h': calls, 'tokens_24h': toks, 'limits': self.limits[kind]}
                if identity:
                    row['identity_calls_24h'] = self._used(c, 'resource LIKE ? AND identity=?', (like, identity), now)[0]
                usd = c.execute("SELECT COALESCE(SUM(list_usd),0) FROM reservations WHERE resource LIKE ? AND ts>=?",
                                (like, now - DAY)).fetchone()[0]
                row['list_usd_24h_not_billed'] = round(float(usd), 4)
                out[kind] = row
        out['plan_block'] = self.plan_check()
        out['note'] = ('tokens = measured model usage; list_usd = API list-price equivalent, not an invoice; '
                       'the Claude plan quota itself is only known as percentage via the bridge')
        return out


def bridge_plan_probe(sock_path: str = '/run/ma-claude/bridge.sock', timeout: float = 4.0):
    """Ask the existing Claude bridge (op 'jobs') for the plan quota it already tracks. Read only."""
    def probe():
        s = socket.socket(socket.AF_UNIX)
        s.settimeout(timeout)
        try:
            s.connect(sock_path)
            s.sendall(b'{"op":"jobs"}\n')
            buf = b''
            while not buf.endswith(b'\n') and len(buf) < 1_000_000:
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
        finally:
            s.close()
        d = json.loads(buf or b'{}')
        plan = d.get('plan') or None
        if plan is not None:
            plan = dict(plan)
            plan['bridge_running_jobs'] = len(d.get('jobs') or [])
        return plan
    return probe
