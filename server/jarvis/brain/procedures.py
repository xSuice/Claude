#!/usr/bin/env python3
"""V10 procedural memory - "chunking" in the spirit of Soar, without a Soar runtime.

A goal that was opened for an observed deviation and finished with every step VERIFIED by
its independent check becomes a *proposed* procedure: trigger (sensor subject + observed
state) -> the exact action/check sequence that fixed it. A human confirms it once
(`procedures.py confirm ID`). From then on the daemon answers the same deviation with that
procedure locally - no Claude call. Outcomes are counted; a procedure that keeps failing is
suspended automatically and needs review again. Nothing here invents commands: procedures
only reference names from the admin action allowlist.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from brain_core import Brain  # noqa: E402

SCHEMA = '''
CREATE TABLE IF NOT EXISTS procedures(
    id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL, project TEXT NOT NULL,
    name TEXT NOT NULL, trigger_subject TEXT NOT NULL, trigger_state TEXT NOT NULL,
    steps TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'proposed'
        CHECK(status IN ('proposed','confirmed','suspended','retired')),
    learned_from TEXT, uses INTEGER NOT NULL DEFAULT 0, successes INTEGER NOT NULL DEFAULT 0,
    failures INTEGER NOT NULL DEFAULT 0, created INTEGER NOT NULL, confirmed INTEGER,
    UNIQUE(owner, project, trigger_subject, trigger_state, steps));
CREATE TABLE IF NOT EXISTS goal_links(
    goal_id TEXT PRIMARY KEY, owner TEXT NOT NULL, project TEXT NOT NULL,
    anomaly_id TEXT, subject TEXT NOT NULL, state TEXT NOT NULL, procedure_id INTEGER,
    kind TEXT NOT NULL CHECK(kind IN ('procedure','diagnosis','manual')),
    outcome TEXT, created INTEGER NOT NULL, closed INTEGER, learned INTEGER NOT NULL DEFAULT 0);
'''
SUSPEND_AFTER = 3  # failures, when failures > successes


class Procedures:
    def __init__(self, brain: Brain):
        self.brain = brain
        with brain.connection(True) as db:
            db.executescript(SCHEMA)
            if 'learned' not in {r[1] for r in db.execute('PRAGMA table_info(goal_links)')}:
                db.execute('ALTER TABLE goal_links ADD COLUMN learned INTEGER NOT NULL DEFAULT 0')

    # ---- linking goals to the deviation they answer ----
    def link(self, goal_id, anomaly_id, subject, state, kind, procedure_id=None):
        with self.brain.connection(True) as db:
            g = db.execute('SELECT owner,project FROM goals WHERE id=?', (goal_id,)).fetchone()
            if not g or g['owner'] != self.brain.identity:
                raise PermissionError('goal not allowed')
            db.execute('INSERT OR REPLACE INTO goal_links(goal_id,owner,project,anomaly_id,subject,state,'
                       'procedure_id,kind,created) VALUES(?,?,?,?,?,?,?,?,?)',
                       (goal_id, self.brain.identity, g['project'], anomaly_id, subject, state, procedure_id,
                        kind, int(time.time())))

    def open_goal_for(self, project, subject) -> str | None:
        with self.brain.connection() as db:
            r = db.execute("SELECT l.goal_id FROM goal_links l JOIN goals g ON g.id=l.goal_id WHERE l.owner=? "
                           "AND l.project=? AND l.subject=? AND g.state='active' LIMIT 1",
                           (self.brain.identity, project, subject)).fetchone()
        return r['goal_id'] if r else None

    # ---- learning ----
    def _goal_steps(self, db, goal_id):
        return db.execute('SELECT s.instruction,s.status,b.action,b.check_action FROM steps s '
                          'LEFT JOIN exec_bindings b ON b.step_id=s.id WHERE s.goal_id=? ORDER BY s.ordinal',
                          (goal_id,)).fetchall()

    def review_closed_goals(self) -> dict:
        """Called after each executive run: closes links, updates stats, proposes new procedures."""
        learned, updated = [], []
        now = int(time.time())
        with self.brain.connection(True) as db:
            rows = db.execute("SELECT l.*,g.state gstate FROM goal_links l JOIN goals g ON g.id=l.goal_id "
                              "WHERE l.owner=? AND l.closed IS NULL", (self.brain.identity,)).fetchall()
            for l in rows:
                steps = self._goal_steps(db, l['goal_id'])
                blocked = any(s['status'] == 'blocked' for s in steps)
                if l['gstate'] == 'completed' and all(s['status'] == 'verified' for s in steps):
                    outcome = 'success'
                elif blocked:
                    outcome = 'failure'
                else:
                    continue
                db.execute('UPDATE goal_links SET outcome=?,closed=? WHERE goal_id=?', (outcome, now, l['goal_id']))
                if outcome == 'failure' and l['kind'] in ('procedure', 'diagnosis'):
                    # close it: the failure is counted and reported; the next deviation gets a fresh attempt
                    db.execute("UPDATE goals SET state='archived' WHERE id=?", (l['goal_id'],))
                if l['procedure_id']:
                    col = 'successes' if outcome == 'success' else 'failures'
                    db.execute(f'UPDATE procedures SET {col}={col}+1 WHERE id=?', (l['procedure_id'],))
                    p = db.execute('SELECT * FROM procedures WHERE id=?', (l['procedure_id'],)).fetchone()
                    if p['failures'] >= SUSPEND_AFTER and p['failures'] > p['successes'] and p['status'] == 'confirmed':
                        db.execute("UPDATE procedures SET status='suspended' WHERE id=?", (p['id'],))
                    updated.append({'procedure': p['id'], 'outcome': outcome})
            # V10.1: learn only from a MANUAL fix whose steps all verified AND whose deviation the sensor
            # has since reported as resolved. A diagnosis or a fix that did not cure the symptom is no procedure.
            cands = db.execute("SELECT l.* FROM goal_links l LEFT JOIN cognitive_anomalies a ON a.id=l.anomaly_id "
                               "WHERE l.owner=? AND l.kind='manual' AND l.outcome='success' AND l.learned=0 "
                               "AND a.status='resolved'", (self.brain.identity,)).fetchall() \
                if db.execute("SELECT 1 FROM sqlite_master WHERE name='cognitive_anomalies'").fetchone() else []
            for l in cands:
                steps = self._goal_steps(db, l['goal_id'])
                db.execute('UPDATE goal_links SET learned=1 WHERE goal_id=?', (l['goal_id'],))
                if not steps or not all(s['action'] and s['status'] == 'verified' for s in steps):
                    continue
                seq = json.dumps([{'instruction': s['instruction'], 'action': s['action'],
                                   'check': s['check_action']} for s in steps], ensure_ascii=False)
                cur = db.execute('INSERT OR IGNORE INTO procedures(owner,project,name,trigger_subject,'
                                 'trigger_state,steps,learned_from,created) VALUES(?,?,?,?,?,?,?,?)',
                                 (self.brain.identity, l['project'], f"{l['subject']}={l['state']}",
                                  l['subject'], l['state'], seq, l['goal_id'], now))
                if cur.rowcount:
                    learned.append({'procedure': cur.lastrowid, 'trigger': f"{l['subject']}={l['state']}"})
        return {'learned': learned, 'updated': updated}

    # ---- use ----
    def match(self, project, subject, state):
        with self.brain.connection() as db:
            rows = db.execute("SELECT * FROM procedures WHERE owner=? AND project=? AND status='confirmed' "
                              "AND trigger_subject=? AND trigger_state IN (?, '*') "
                              "ORDER BY (successes+1.0)/(successes+failures+2.0) DESC, id ASC",
                              (self.brain.identity, project, subject, state)).fetchall()
        return [dict(r) for r in rows]

    def instantiate(self, executive, proc: dict, anomaly_id: str | None, subject: str, state: str,
                    idem_key: str | None = None) -> dict:
        steps = json.loads(proc['steps'])
        for s in steps:
            if s['action'] not in executive.actions or s['check'] not in executive.actions:
                raise ValueError(f"procedure {proc['id']} references an action that is no longer allowlisted")
        risk = 'privileged' if any(executive.actions[s[k]].get('risk') == 'privileged'
                                   for s in steps for k in ('action', 'check')) else 'reversible'
        g = executive.orders.open(proc['project'], f"Ablauf #{proc['id']}: {subject}={state}"[:160],
                                  f"{subject} wieder im Sollzustand", [s['instruction'] for s in steps], priority=1,
                                  idem_key=idem_key or f"procedure:{proc['id']}:{anomaly_id}", risk=risk,
                                  quality=f'all checks pass: {[s["check"] for s in steps]}')
        if g['duplicate']:
            return {'goal_id': g['goal_id'], 'procedure': proc['id'], 'steps': len(steps), 'duplicate': True}
        with self.brain.connection() as db:
            ids = [r['id'] for r in db.execute('SELECT id FROM steps WHERE goal_id=? ORDER BY ordinal', (g['goal_id'],))]
        for sid, s in zip(ids, steps):
            executive.bind(proc['project'], sid, s['action'], s['check'], by='admin')  # confirmed by the operator
        self.link(g['goal_id'], anomaly_id, subject, state, 'procedure', proc['id'])
        with self.brain.connection(True) as db:
            db.execute('UPDATE procedures SET uses=uses+1 WHERE id=?', (proc['id'],))
        return {'goal_id': g['goal_id'], 'procedure': proc['id'], 'steps': len(steps)}

    # ---- operator ----
    def set_status(self, pid: int, status: str) -> dict:
        if status not in ('confirmed', 'retired', 'suspended'):
            raise ValueError('status')
        with self.brain.connection(True) as db:
            cur = db.execute('UPDATE procedures SET status=?,confirmed=? WHERE id=? AND owner=?',
                             (status, int(time.time()) if status == 'confirmed' else None, pid, self.brain.identity))
            if cur.rowcount != 1:
                raise PermissionError('procedure not found')
        return {'procedure': pid, 'status': status}

    def listing(self, project=None) -> list[dict]:
        with self.brain.connection() as db:
            q = 'SELECT id,project,name,status,uses,successes,failures,steps,learned_from FROM procedures WHERE owner=?'
            args = [self.brain.identity]
            if project:
                q += ' AND project=?'; args.append(project)
            return [{**dict(r), 'steps': json.loads(r['steps'])} for r in db.execute(q + ' ORDER BY id', args)]


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--config', type=Path, required=True)
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('list').add_argument('--project')
    for c in ('confirm', 'retire', 'suspend'):
        sub.add_parser(c).add_argument('id', type=int)
    a = p.parse_args()
    try:
        conf = json.loads(a.config.resolve(strict=True).read_text(encoding='utf-8'))
        db = Path(conf['state_db']).expanduser()
        if not db.is_absolute(): db = (a.config.resolve().parent / db).resolve()
        pr = Procedures(Brain(db, conf['identity'], set(conf['allowed_projects'])))
        out = pr.listing(a.project) if a.cmd == 'list' else pr.set_status(
            a.id, {'confirm': 'confirmed', 'retire': 'retired', 'suspend': 'suspended'}[a.cmd])
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    except (OSError, ValueError, KeyError, PermissionError) as e:
        print(f'ERROR: {type(e).__name__}: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
