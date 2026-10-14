"""V10.1 order model on top of the existing goals/steps (no second task system).

Every goal opened by the daemon (or anyone using this API) carries: owner/project (from the
goal), an idempotency key that is UNIQUE per owner+project at database level, a risk tier,
a Claude call budget, an optional deadline, the quality requirement it is judged by, and a
cancel flag. The same sensor/timer event can therefore never open a second goal - not even
from a second daemon process. Kill switch: a file named KILL next to the brain DB stops all
actions immediately (perception and heartbeat continue).
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

RISKS = ('read', 'reversible', 'privileged')
SCHEMA = '''CREATE TABLE IF NOT EXISTS goal_meta(
    goal_id TEXT PRIMARY KEY, owner TEXT NOT NULL, project TEXT NOT NULL, idem_key TEXT NOT NULL,
    risk TEXT NOT NULL CHECK(risk IN ('read','reversible','privileged')),
    claude_budget INTEGER NOT NULL DEFAULT 0, claude_used INTEGER NOT NULL DEFAULT 0,
    deadline INTEGER, quality TEXT, topic TEXT, created INTEGER NOT NULL, cancelled INTEGER NOT NULL DEFAULT 0,
    UNIQUE(owner, project, idem_key))'''


def killed(brain) -> bool:
    return (brain.db_path.parent / 'KILL').exists()


class Orders:
    def __init__(self, brain):
        self.brain = brain
        with brain.connection(True) as db:
            db.execute(SCHEMA)
            cols = {r[1] for r in db.execute('PRAGMA table_info(goal_meta)')}
            for col, ddl in (('helper_budget', 'INTEGER NOT NULL DEFAULT 0'), ('helper_used', 'INTEGER NOT NULL DEFAULT 0'),
                             ('data_class', "TEXT NOT NULL DEFAULT 'internal'")):
                if col not in cols:  # V11: helper budget + data class per order
                    db.execute(f'ALTER TABLE goal_meta ADD COLUMN {col} {ddl}')

    def open(self, project, title, desired, steps, *, idem_key, priority=3, risk='reversible',
             claude_budget=0, deadline=None, quality=None, topic=None, helper_budget=0, data_class='internal') -> dict:
        """Idempotent: a second call with the same key returns the first goal, creates nothing."""
        if risk not in RISKS:
            raise ValueError('risk must be read, reversible or privileged')
        if not isinstance(idem_key, str) or not 3 <= len(idem_key) <= 200:
            raise ValueError('idem_key 3..200 chars')
        if type(claude_budget) is not int or not 0 <= claude_budget <= 5:
            raise ValueError('claude_budget 0..5')
        if type(helper_budget) is not int or not 0 <= helper_budget <= 5:
            raise ValueError('helper_budget 0..5')
        if data_class not in ('public', 'internal', 'private', 'secret'):
            raise ValueError('data_class')
        project = self.brain._project(project)
        with self.brain.connection() as db:
            r = db.execute('SELECT goal_id FROM goal_meta WHERE owner=? AND project=? AND idem_key=?',
                           (self.brain.identity, project, idem_key)).fetchone()
        if r:
            return {'goal_id': r[0], 'duplicate': True}
        g = self.brain.new_goal(project, title, desired, steps, priority)
        try:
            with self.brain.connection(True) as db:
                db.execute('INSERT INTO goal_meta(goal_id,owner,project,idem_key,risk,claude_budget,deadline,quality,'
                           'topic,created,helper_budget,data_class) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                           (g['goal_id'], self.brain.identity, project, idem_key, risk, claude_budget, deadline,
                            quality, topic, int(time.time()), helper_budget, data_class))
        except sqlite3.IntegrityError:
            # lost a race against another process: withdraw ours, return theirs
            with self.brain.connection(True) as db:
                db.execute('DELETE FROM steps WHERE goal_id=?', (g['goal_id'],))
                db.execute('DELETE FROM goals WHERE id=?', (g['goal_id'],))
                r = db.execute('SELECT goal_id FROM goal_meta WHERE owner=? AND project=? AND idem_key=?',
                               (self.brain.identity, project, idem_key)).fetchone()
            return {'goal_id': r[0], 'duplicate': True}
        return {'goal_id': g['goal_id'], 'duplicate': False}

    def meta(self, goal_id):
        with self.brain.connection() as db:
            r = db.execute('SELECT * FROM goal_meta WHERE goal_id=?', (goal_id,)).fetchone()
        return dict(r) if r else None

    def charge_claude(self, goal_id) -> bool:
        """Atomically use one unit of the goal's Claude budget; False if exhausted."""
        with self.brain.connection(True) as db:
            r = db.execute('SELECT 1 FROM goal_meta WHERE goal_id=?', (goal_id,)).fetchone()
            if r is None:
                return True  # goals without meta: only the queue's own limits apply
            cur = db.execute('UPDATE goal_meta SET claude_used=claude_used+1 WHERE goal_id=? AND '
                             'claude_used<claude_budget AND cancelled=0', (goal_id,))
            return cur.rowcount == 1

    def charge_helper(self, goal_id) -> bool:
        with self.brain.connection(True) as db:
            cur = db.execute('UPDATE goal_meta SET helper_used=helper_used+1 WHERE goal_id=? AND '
                             'helper_used<helper_budget AND cancelled=0', (goal_id,))
            return cur.rowcount == 1

    def cancel(self, goal_id, reason='cancelled by operator') -> dict:
        now = int(time.time())
        with self.brain.connection(True) as db:
            g = db.execute('SELECT owner FROM goals WHERE id=?', (goal_id,)).fetchone()
            if not g or g[0] != self.brain.identity:
                raise PermissionError('goal not allowed')
            db.execute("UPDATE goals SET state='archived' WHERE id=?", (goal_id,))
            db.execute('UPDATE goal_meta SET cancelled=1 WHERE goal_id=?', (goal_id,))
            db.execute("UPDATE steps SET status='blocked',outcome=?,updated=? WHERE goal_id=? AND status='pending'",
                       (reason, now, goal_id))
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='exec_bindings'").fetchone():
                db.execute("UPDATE exec_bindings SET state='failed',updated=? WHERE step_id IN "
                           "(SELECT id FROM steps WHERE goal_id=?) AND state IN ('ready','awaiting_approval')",
                           (now, goal_id))
        return {'goal_id': goal_id, 'state': 'archived', 'reason': reason}

    def expire(self, now) -> list[str]:
        with self.brain.connection() as db:
            ids = [r[0] for r in db.execute("SELECT m.goal_id FROM goal_meta m JOIN goals g ON g.id=m.goal_id WHERE "
                                            "m.owner=? AND g.state='active' AND m.deadline IS NOT NULL AND m.deadline<?",
                                            (self.brain.identity, now))]
        for gid in ids:
            self.cancel(gid, 'deadline passed')
        return ids
