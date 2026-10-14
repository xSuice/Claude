#!/usr/bin/env python3
"""V11.1 honest scoreboard: verified results per resource, from data the system already records.

Main metric (audit): verified tasks / total consumption. Reported side by side, never merged into one
"savings" number: verified orders, rework (same failure again within 7 days), where each verified step
came from (local procedure / helper / Claude), Claude jobs + tokens + list-price cost as reported by
Claude Code, helper calls + tokens + cost, the brain's own CPU. The Pro quota is NOT observable here;
Claude cost is the API list-price equivalent Claude Code reports, which with a Pro login is consumed
from the Pro quota instead of being billed.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path


def _has(db, table):
    return db.execute("SELECT 1 FROM sqlite_master WHERE name=?", (table,)).fetchone() is not None


def build(brain, days=7, queue_db: Path | None = None, helpers_db: Path | None = None, perf_db: Path | None = None,
          now: int | None = None) -> dict:
    now = int(time.time()) if now is None else now
    since, me = now - days * 86400, brain.identity
    out = {'days': days, 'identity': me}
    with brain.connection() as db:
        if _has(db, 'goal_meta'):
            g = db.execute('''SELECT COUNT(*) n,
                   SUM(NOT EXISTS(SELECT 1 FROM steps s WHERE s.goal_id=m.goal_id AND s.status!='verified')) done,
                   SUM(EXISTS(SELECT 1 FROM steps s WHERE s.goal_id=m.goal_id AND s.status='blocked')) blocked,
                   SUM(m.claude_used) claude_used FROM goal_meta m WHERE m.owner=? AND m.created>=?''', (me, since)).fetchone()
            out['orders'] = {'opened': g[0], 'verified': g[1] or 0, 'blocked': g[2] or 0, 'claude_charged': g[3] or 0}
        src = {'local': 0, 'helper': 0, 'claude': 0}
        meta = _has(db, 'goal_meta')
        for sid, claude_used in db.execute(
                "SELECT s.id, " + ("(SELECT claude_used FROM goal_meta m WHERE m.goal_id=s.goal_id)" if meta else "0") +
                " FROM steps s JOIN goals g ON g.id=s.goal_id WHERE g.owner=? AND s.status='verified' AND s.updated>=?",
                (me, since)).fetchall():
            helper = db.execute("SELECT 1 FROM exec_runs WHERE step_id=? AND kind='check' AND action LIKE 'verify:%' AND exit=0",
                                (sid,)).fetchone()
            src['helper' if helper else 'claude' if claude_used else 'local'] += 1
        steps_ok = sum(src.values())
        out['verified_steps'] = {'total': steps_ok, **src}
        if _has(db, 'cognitive_anomalies'):
            subj = [r[0] for r in db.execute(
                'SELECT e.subject FROM cognitive_anomalies a JOIN cognitive_events e ON e.id=a.event_id '
                'WHERE a.owner=? AND a.created>=?', (me, since))]
            out['failures'] = {'anomalies': len(subj), 'distinct': len(set(subj)),
                               'rework_repeats': len(subj) - len(set(subj))}   # same subject failing again
    if queue_db and Path(queue_db).exists():
        c = sqlite3.connect(str(queue_db))
        try:
            rows = c.execute('SELECT status, model_usage FROM jobs WHERE owner=? AND created>=?', (me, since)).fetchall()
        finally:
            c.close()
        tok = cost = 0
        for _, u in rows:
            try:
                u = json.loads(u or '{}')
            except ValueError:
                u = {}
            uu = u.get('usage') or {}
            tok += sum(int(uu.get(k) or 0) for k in ('input_tokens', 'output_tokens', 'cache_creation_input_tokens'))
            cost += float(u.get('total_cost_usd') or 0)
        out['claude'] = {'jobs': len(rows), 'done': sum(r[0] == 'done' for r in rows), 'failed': sum(r[0] == 'failed' for r in rows),
                         'tokens_uncached': tok, 'list_price_usd': round(cost, 4),
                         'note': 'mit Pro-Login aus dem Pro-Kontingent statt abgerechnet; Kontingent selbst nicht messbar'}
    if helpers_db and Path(helpers_db).exists():
        c = sqlite3.connect(str(helpers_db))
        try:
            h = c.execute("SELECT COUNT(*), SUM(status='ok'), SUM(verified=1), SUM(verified=0), "
                          "SUM(COALESCE(in_tokens,0)+COALESCE(out_tokens,0)), SUM(COALESCE(cost_usd,0)) "
                          "FROM helper_calls WHERE identity=? AND ts>=? AND status!='refused'", (me, since)).fetchone()
        finally:
            c.close()
        out['helpers'] = {'calls': h[0], 'answers': h[1] or 0, 'verified_ok': h[2] or 0, 'verified_bad': h[3] or 0,
                          'tokens': h[4] or 0, 'usd': round(h[5] or 0, 4)}
    if perf_db and Path(perf_db).exists():
        c = sqlite3.connect(str(perf_db))
        try:
            v = [json.loads(r[0]).get('self_cpu_pct') for r in c.execute('SELECT data FROM perf_raw WHERE ts>=?', (since,))]
        finally:
            c.close()
        v = [x for x in v if x is not None]
        out['brain_self_cpu_pct_avg'] = round(sum(v) / len(v), 2) if v else None
    vs = out['verified_steps']['total']
    cl = out.get('claude', {})
    out['kpi'] = {'verified_steps_per_claude_job': round(vs / cl['jobs'], 2) if cl.get('jobs') else None,
                  'claude_tokens_per_verified_step': round(cl['tokens_uncached'] / vs) if cl.get('jobs') and vs else None,
                  'share_without_claude': round((vs - out['verified_steps']['claude']) / vs, 3) if vs else None}
    return out
