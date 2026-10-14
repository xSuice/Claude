#!/usr/bin/env python3
"""V10 digital self-model, homeostasis, doctor and long-term metrics. Local, no LLM.

snapshot  What the brain can do (sensors, actions, procedures, Claude route), what it may
          spend (budgets used vs. limits), how it is (DB, heartbeat, load, memory, disk),
          where it is weak (recurring verified failures, blocked steps, suspended procedures)
          and, per open deviation, whether it is known (procedure), needs a diagnosis or
          has no permitted action.
doctor    Verifiable safety/isolation findings: file permissions, one identity per DB,
          sandbox availability, stale heartbeat.
metrics   Daily rollup kept for long-term comparisons (verified/blocked steps, local runs,
          Claude jobs, anomalies and time-to-recovery, procedure success, trials, rated tasks).
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import time
from datetime import date, datetime, timedelta
from pathlib import Path

METRICS = '''CREATE TABLE IF NOT EXISTS metrics_daily(
    owner TEXT NOT NULL, day TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY(owner, day))'''
DEFAULT_LIMITS = {'max_load_per_cpu': 1.5, 'min_mem_mb': 256, 'min_disk_percent': 5.0}


def homeostasis(state_dir: Path, limits: dict | None = None) -> dict:
    lim = {**DEFAULT_LIMITS, **(limits or {})}
    out = {'cpus': os.cpu_count() or 1}
    try:
        out['load_per_cpu'] = round(os.getloadavg()[0] / out['cpus'], 2)
    except OSError:
        out['load_per_cpu'] = None
    try:
        with open('/proc/meminfo') as fh:
            info = {l.split(':')[0]: int(l.split()[1]) for l in fh if l.split()[1:2]}
        out['mem_available_mb'] = info.get('MemAvailable', 0) // 1024
    except (OSError, ValueError, IndexError):
        out['mem_available_mb'] = None
    try:
        u = shutil.disk_usage(state_dir)
        out['disk_free_percent'] = round(100 * u.free / u.total, 1)
    except OSError:
        out['disk_free_percent'] = None
    reasons = []
    if out['load_per_cpu'] is not None and out['load_per_cpu'] > lim['max_load_per_cpu']:
        reasons.append('cpu load')
    if out['mem_available_mb'] is not None and out['mem_available_mb'] < lim['min_mem_mb']:
        reasons.append('memory')
    if out['disk_free_percent'] is not None and out['disk_free_percent'] < lim['min_disk_percent']:
        reasons.append('disk')
    out['mode'] = 'conserve' if reasons else 'normal'
    out['reasons'] = reasons
    return out


def _count(db, sql, args=()):
    try:
        return db.execute(sql, args).fetchone()[0]
    except Exception:  # table may not exist yet in a fresh install
        return 0


def snapshot(brain, project: str, executive=None, procedures=None, sensors_cfg=None, autonomy_cfg=None,
             limits=None) -> dict:
    project = brain._project(project)
    me, now = brain.identity, int(time.time())
    day = now - 86400
    with brain.connection() as db:
        hb = db.execute("SELECT * FROM daemon_state WHERE owner=?", (me,)).fetchone() if _count(
            db, "SELECT COUNT(*) FROM sqlite_master WHERE name='daemon_state'") else None
        weak = [dict(r) for r in db.execute(
            "SELECT task_type, COUNT(*) failures FROM episodes WHERE owner=? AND project=? AND verified=1 "
            "AND outcome='failure' AND created>=? GROUP BY task_type ORDER BY failures DESC LIMIT 5",
            (me, project, now - 30 * 86400))]
        blocked = _count(db, "SELECT COUNT(*) FROM steps s JOIN goals g ON g.id=s.goal_id WHERE g.owner=? AND "
                             "g.project=? AND g.state='active' AND s.status='blocked'", (me, project))
        anomalies = [dict(r) for r in db.execute(
            "SELECT a.id,e.subject,v.value,v.severity FROM cognitive_anomalies a JOIN cognitive_events v ON "
            "v.id=a.event_id JOIN cognitive_expectations e ON e.id=a.expectation_id WHERE a.owner=? AND "
            "a.project=? AND a.status='open' AND e.active=1 ORDER BY v.severity DESC LIMIT 10", (me, project))] \
            if _count(db, "SELECT COUNT(*) FROM sqlite_master WHERE name='cognitive_anomalies'") else []
        local_runs = _count(db, "SELECT COUNT(*) FROM exec_runs WHERE owner=? AND started>=? AND kind!='claude'", (me, day))
        trials = _count(db, "SELECT COUNT(*) FROM improvement_trials WHERE owner=? AND created>=?", (me, day))
        procs = {r[0]: r[1] for r in db.execute(
            "SELECT status, COUNT(*) FROM procedures WHERE owner=? AND project=? GROUP BY status", (me, project))} \
            if _count(db, "SELECT COUNT(*) FROM sqlite_master WHERE name='procedures'") else {}
        memories = _count(db, "SELECT COUNT(*) FROM memory WHERE owner=? AND project=? AND status='confirmed'", (me, project))
    claude = {'queue_enabled': bool(autonomy_cfg and autonomy_cfg.get('enabled'))}
    if autonomy_cfg:
        from autonomy import Queue
        with Queue(autonomy_cfg['db_path']).connect() as c:
            claude['jobs_24h'] = c.execute('SELECT COUNT(*) FROM jobs WHERE started>=?', (day,)).fetchone()[0]
        claude['max_jobs_per_day'] = autonomy_cfg['max_jobs_per_day']
        claude['templates'] = autonomy_cfg['allowed_templates']
    decisions = []
    for a in anomalies:
        known = procedures.match(project, a['subject'], a['value']) if procedures else []
        if known:
            decisions.append({'subject': a['subject'], 'state': a['value'], 'decision': f"known: procedure #{known[0]['id']}"})
        elif a['severity'] >= 4 and claude['queue_enabled']:
            decisions.append({'subject': a['subject'], 'state': a['value'], 'decision': 'unknown: diagnosis by Claude (queued, budgeted)'})
        else:
            decisions.append({'subject': a['subject'], 'state': a['value'], 'decision': 'unknown: needs human review'})
    acts = executive.actions if executive else {}
    return {
        'identity': me, 'project': project, 'claude_calls_by_this_snapshot': 0,
        'health': {'database_ok': brain_ok(brain), 'paused': _paused(brain, project),
                   'heartbeat_age_s': (now - hb['last_tick']) if hb else None,
                   'daemon_errors': hb['errors'] if hb else None, **homeostasis(brain.db_path.parent, limits)},
        'capabilities': {'sensors': [s['id'] for s in (sensors_cfg or {}).get('sensors', [])],
                         'actions': {k: ('claude' if 'claude_template' in v else 'local') +
                                     (' auto' if v.get('auto') else '') + (' sandboxed' if v.get('sandbox') else '')
                                     for k, v in acts.items()},
                         'procedures': procs, 'confirmed_memories': memories, 'claude_route': claude},
        'budget': {'local_runs_24h': local_runs,
                   'local_runs_limit': executive.limits['max_local_runs_per_day'] if executive else None,
                   'trials_24h': trials},
        'weaknesses': {'recurring_verified_failures_30d': weak, 'blocked_steps': blocked,
                       'suspended_procedures': procs.get('suspended', 0)},
        'open_deviations': decisions,
    }


def brain_ok(brain) -> bool:
    with brain.connection() as db:
        return db.execute('PRAGMA quick_check(1)').fetchone()[0] == 'ok'


def _paused(brain, project) -> bool:
    with brain.connection() as db:
        r = db.execute('SELECT paused FROM cognitive_control WHERE owner=? AND project=?',
                       (brain.identity, project)).fetchone() if _count(
            db, "SELECT COUNT(*) FROM sqlite_master WHERE name='cognitive_control'") else None
    return bool(r and r[0])


OWNER_TABLES = ('memory', 'goals', 'episodes', 'suggestions', 'cognitive_events', 'exec_bindings',
                'experience_runs', 'procedures', 'improvement_trials')


def doctor(brain, config_paths: list[Path] = (), strict_identity: bool = False, heartbeat_max_s: int = 3600) -> dict:
    findings = []
    def add(level, what, detail):
        findings.append({'level': level, 'check': what, 'detail': detail})
    if os.name == 'posix':
        for p in [brain.db_path, *map(Path, config_paths)]:
            try:
                mode = stat.S_IMODE(p.stat().st_mode)
            except OSError:
                continue
            if mode & 0o077:
                add('error' if p == brain.db_path or mode & 0o022 else 'warning', 'permissions',
                    f'{p.name}: mode {oct(mode)} - should be 600')
            if p.stat().st_uid != os.getuid():
                add('warning', 'ownership', f'{p.name} is owned by another OS user')
    owners = set()
    with brain.connection() as db:
        names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for t in OWNER_TABLES:
            if t in names:
                owners |= {r[0] for r in db.execute(f'SELECT DISTINCT owner FROM {t}')}
        hb = db.execute("SELECT last_tick FROM daemon_state WHERE owner=?", (brain.identity,)).fetchone() \
            if 'daemon_state' in names else None
    others = sorted(owners - {brain.identity})
    if others:
        add('error' if strict_identity else 'warning', 'identity isolation',
            f'database also holds data of {len(others)} other identity/identities - separation is program-level only; '
            'use one DB file (and OS user) per person')
    import sandbox
    if not sandbox.available():
        add('error', 'sandbox', 'namespaces unavailable: improvement trials will refuse to run')
    if hb and time.time() - hb[0] > heartbeat_max_s:
        add('warning', 'heartbeat', f'daemon silent for {int(time.time() - hb[0])} s')
    if not brain_ok(brain):
        add('error', 'database', 'integrity check failed')
    return {'ok': not any(f['level'] == 'error' for f in findings), 'findings': findings}


def rollup(brain, day: date) -> dict:
    """Store one day's numbers (local time boundaries) for long-term comparison."""
    start = int(datetime.combine(day, datetime.min.time()).timestamp()); end = start + 86400
    me = brain.identity
    with brain.connection(True) as db:
        db.execute(METRICS)
        q = lambda sql, a=(): _count(db, sql, a)  # noqa: E731
        ttr = [r[0] for r in db.execute(
            'SELECT resolved_at-created FROM cognitive_anomalies WHERE owner=? AND resolved_at>=? AND resolved_at<?',
            (me, start, end))] if 'resolved_at' in {c[1] for c in db.execute('PRAGMA table_info(cognitive_anomalies)')} else []
        data = {
            'steps_verified': q("SELECT COUNT(*) FROM steps s JOIN goals g ON g.id=s.goal_id WHERE g.owner=? AND "
                                "s.status='verified' AND s.updated>=? AND s.updated<?", (me, start, end)),
            'steps_blocked': q("SELECT COUNT(*) FROM steps s JOIN goals g ON g.id=s.goal_id WHERE g.owner=? AND "
                               "s.status='blocked' AND s.updated>=? AND s.updated<?", (me, start, end)),
            'local_runs': q("SELECT COUNT(*) FROM exec_runs WHERE owner=? AND kind!='claude' AND started>=? AND started<?", (me, start, end)),
            'claude_jobs_queued': q("SELECT COUNT(*) FROM exec_runs WHERE owner=? AND kind='claude' AND started>=? AND started<?", (me, start, end)),
            'anomalies_opened': q('SELECT COUNT(*) FROM cognitive_anomalies WHERE owner=? AND created>=? AND created<?', (me, start, end)),
            'anomalies_resolved': len(ttr),
            'median_time_to_recovery_s': sorted(ttr)[len(ttr) // 2] if ttr else None,
            'procedure_runs': q("SELECT COUNT(*) FROM goal_links WHERE owner=? AND kind='procedure' AND closed>=? AND closed<?", (me, start, end)),
            'procedure_successes': q("SELECT COUNT(*) FROM goal_links WHERE owner=? AND kind='procedure' AND outcome='success' AND closed>=? AND closed<?", (me, start, end)),
            'trials': q('SELECT COUNT(*) FROM improvement_trials WHERE owner=? AND created>=? AND created<?', (me, start, end)),
            'tasks_rated': q('SELECT COUNT(*) FROM experience_tasks WHERE owner=? AND rated>=? AND rated<?', (me, start, end)),
            'tasks_success': q("SELECT COUNT(*) FROM experience_tasks WHERE owner=? AND outcome='success' AND rated>=? AND rated<?", (me, start, end)),
            'rework_minutes': q('SELECT COALESCE(SUM(rework_minutes),0) FROM experience_tasks WHERE owner=? AND rated>=? AND rated<?', (me, start, end)),
        }
        db.execute('INSERT OR REPLACE INTO metrics_daily VALUES(?,?,?)', (me, day.isoformat(), json.dumps(data)))
    return {'day': day.isoformat(), **data}


def history(brain, days: int = 30) -> list[dict]:
    with brain.connection(True) as db:
        db.execute(METRICS)
        since = (date.today() - timedelta(days=days)).isoformat()
        return [{'day': r[0], **json.loads(r[1])} for r in db.execute(
            'SELECT day,data FROM metrics_daily WHERE owner=? AND day>=? ORDER BY day', (brain.identity, since))]
