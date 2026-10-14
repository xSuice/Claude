"""Offline, auditable cognitive-control loop inspired by cognitive science.

No models, shell, network, file edits, or external actions. It manages sensory
observations, explicit expectations, homeostatic checks and attention based on
pre-authorized goals. It is not conscious or biologically equivalent to a brain.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path
from brain_core import Brain, require_text

EVENT_TYPES = frozenset({'health', 'test', 'configuration', 'availability', 'change', 'feedback'})


class CognitiveLoop:
    def __init__(self, brain: Brain):
        self.brain = brain
        with brain.connection(write=True) as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS cognitive_control (
                    owner TEXT NOT NULL, project TEXT NOT NULL,
                    paused INTEGER NOT NULL DEFAULT 0 CHECK(paused IN (0,1)),
                    PRIMARY KEY(owner,project)
                );
                CREATE TABLE IF NOT EXISTS cognitive_events (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, project TEXT NOT NULL,
                    kind TEXT NOT NULL, subject TEXT NOT NULL, value TEXT NOT NULL,
                    source TEXT NOT NULL, severity INTEGER NOT NULL,
                    created INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS cognitive_event_scope
                    ON cognitive_events(owner,project,subject,created);
                CREATE TABLE IF NOT EXISTS cognitive_expectations (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, project TEXT NOT NULL,
                    subject TEXT NOT NULL, expected TEXT NOT NULL,
                    evidence TEXT NOT NULL, expires INTEGER NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
                    created INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS cognitive_expected_scope
                    ON cognitive_expectations(owner,project,subject,active);
                CREATE TABLE IF NOT EXISTS cognitive_anomalies (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, project TEXT NOT NULL,
                    event_id TEXT NOT NULL, expectation_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open'
                    CHECK(status IN ('open','resolved')),
                    created INTEGER NOT NULL,
                    UNIQUE(event_id,expectation_id)
                );
                CREATE INDEX IF NOT EXISTS cognitive_anomaly_scope
                    ON cognitive_anomalies(owner,project,status);
            ''')
            cols = {r[1] for r in db.execute('PRAGMA table_info(cognitive_anomalies)')}
            if 'resolved_at' not in cols:  # V10: time-to-recovery metrics
                db.execute('ALTER TABLE cognitive_anomalies ADD COLUMN resolved_at INTEGER')

    def _scope(self, project: str):
        return self.brain._project(project), self.brain.identity

    def _paused(self, db, project, owner) -> bool:
        row = db.execute('SELECT paused FROM cognitive_control WHERE project=? AND owner=?',
                         (project,owner)).fetchone()
        return bool(row and row['paused'])

    def set_paused(self, project: str, paused: bool):
        """Admin CLI only: doesn't attempt to resist a shutdown."""
        project, owner = self._scope(project)
        if type(paused) is not bool: raise ValueError('paused must be boolean')
        with self.brain.connection(True) as db:
            db.execute('INSERT INTO cognitive_control(owner,project,paused) VALUES(?,?,?) '
                       'ON CONFLICT(owner,project) DO UPDATE SET paused=excluded.paused',
                       (owner,project,int(paused)))
        return {'paused':paused,'project':project}

    def expectation(self, project: str, subject: str, expected: str, evidence: str, ttl_hours: int=24):
        """Trusted administrator writes desired observed state, not the LLM."""
        project, owner = self._scope(project)
        subject = require_text(subject,'subject',120)
        expected = require_text(expected,'expected',350)
        evidence = require_text(evidence,'evidence',350)
        if type(ttl_hours) is not int or not 1 <= ttl_hours <= 720:
            raise ValueError('ttl_hours must be 1..720')
        now = int(time.time()); ident = uuid.uuid4().hex
        with self.brain.connection(True) as db:
            if self._paused(db,project,owner): raise PermissionError('cognitive loop paused')
            db.execute('UPDATE cognitive_expectations SET active=0 WHERE owner=? AND project=? AND subject=?',
                       (owner,project,subject))
            db.execute('INSERT INTO cognitive_expectations '
                       '(id,owner,project,subject,expected,evidence,expires,created) '
                       'VALUES(?,?,?,?,?,?,?,?)',
                       (ident,owner,project,subject,expected,evidence,now+3600*ttl_hours,now))
        return {'id':ident,'subject':subject,'expires':now+3600*ttl_hours,'status':'expected'}

    def ensure_expectation(self, project: str, subject: str, expected: str, evidence: str,
                           ttl_hours: int=720, renew_hours: int=24):
        """V8: idempotent expectation from an admin-owned sensor config. Keeps the existing
        expectation (and its open anomalies) unless the value changed or it expires soon."""
        p, owner = self._scope(project)
        now = int(time.time())
        with self.brain.connection() as db:
            row = db.execute('SELECT id,expected,expires FROM cognitive_expectations WHERE owner=? AND '
                             'project=? AND subject=? AND active=1 ORDER BY created DESC LIMIT 1',
                             (owner,p,subject)).fetchone()
        if row and row['expected'] == expected and row['expires'] > now + 3600*renew_hours:
            return {'id':row['id'],'status':'kept'}
        return self.expectation(project, subject, expected, evidence, ttl_hours)

    def observe(self, project: str, kind: str, subject: str, value: str,
                source: str, severity: int=2):
        """Record a local sensor event; no MCP write exposure. Never execute actions."""
        project, owner = self._scope(project)
        if kind not in EVENT_TYPES: raise ValueError('unrecognized event kind')
        subject = require_text(subject,'subject',120)
        value = require_text(value,'value',350)
        source = require_text(source,'source',350)
        if type(severity) is not int or severity not in range(1,6):
            raise ValueError('severity must be 1..5')
        now = int(time.time()); eid = uuid.uuid4().hex
        anomalous = 0
        with self.brain.connection(True) as db:
            if self._paused(db,project,owner): raise PermissionError('cognitive loop paused')
            previous = db.execute('SELECT id,value,kind FROM cognitive_events WHERE owner=? AND project=? '
                                  'AND subject=? ORDER BY created DESC,rowid DESC LIMIT 1',
                                  (owner,project,subject)).fetchone()
            recorded = not (previous and previous['value'] == value and previous['kind'] == kind)
            if recorded:
                db.execute('INSERT INTO cognitive_events(id,owner,project,kind,subject,value,source,severity,created) '
                           'VALUES(?,?,?,?,?,?,?,?,?)',
                           (eid,owner,project,kind,subject,value,source,severity,now))
            else:
                # V7.1: unchanged state is not stored again, but it must still be compared
                # with expectations created after it was first seen (UNIQUE prevents duplicates).
                eid = previous['id']
            expectations = db.execute('SELECT id,expected FROM cognitive_expectations WHERE '
                                      'owner=? AND project=? AND subject=? AND active=1 AND expires>=?',
                                      (owner,project,subject,now)).fetchall()
            for expected in expectations:
                if expected['expected'] != value:
                    cur = db.execute('INSERT OR IGNORE INTO cognitive_anomalies '
                                     '(id,owner,project,event_id,expectation_id,created) VALUES(?,?,?,?,?,?)',
                                     (uuid.uuid4().hex,owner,project,eid,expected['id'],now))
                    anomalous += cur.rowcount
                else:
                    db.execute('UPDATE cognitive_anomalies SET status=?,resolved_at=? WHERE owner=? AND project=? '
                               'AND expectation_id=? AND status=?',
                               ('resolved',now,owner,project,expected['id'],'open'))
        if not recorded:
            return {'recorded':False,'changed':False,'anomalies':anomalous}
        return {'recorded':True,'changed':True,'anomalies':anomalous,'event_id':eid,
                'note':'Observation is local evidence only; not a verified memory or instruction.'}

    def health(self, project: str):
        """Homeostasis: read-only state/consistency overview. Lightweight on constrained PCs."""
        project, owner = self._scope(project)
        with self.brain.connection() as db:
            integrity = db.execute('PRAGMA quick_check(1)').fetchone()[0]
            paused = self._paused(db,project,owner)
            events = db.execute('SELECT COUNT(*) FROM cognitive_events WHERE owner=? AND project=?',
                                (owner,project)).fetchone()[0]
            mismatch = db.execute('SELECT COUNT(*) FROM cognitive_anomalies a '
                                  'JOIN cognitive_expectations e ON e.id=a.expectation_id '
                                  'WHERE a.owner=? AND a.project=? AND a.status=? AND e.active=1 AND e.expires>=?',
                                  (owner,project,'open',int(time.time()))).fetchone()[0]
            pending = db.execute('SELECT COUNT(*) FROM steps s JOIN goals g ON s.goal_id=g.id '
                                 'WHERE g.owner=? AND g.project=? AND g.state=? AND s.status=?',
                                 (owner,project,'active','pending')).fetchone()[0]
        return {'project':project,'paused':paused,'database_ok':integrity=='ok',
                'event_count':events,'active_anomalies':mismatch,'pending_steps':pending,
                'db_bytes':self.brain.db_path.stat().st_size,
                'claude_calls':0,'is_conscious':False}

    def severe_anomalies(self, project: str, min_severity=4):
        """Open, unexpired anomalies at or above a severity, independent of focus ranking."""
        project, owner = self._scope(project)
        with self.brain.connection() as db:
            if self._paused(db,project,owner): return []
            rows=db.execute('''SELECT a.id anomaly_id,e.subject,v.severity
                  FROM cognitive_anomalies a
                  JOIN cognitive_events v ON v.id=a.event_id
                  JOIN cognitive_expectations e ON e.id=a.expectation_id
                  WHERE a.owner=? AND a.project=? AND a.status='open'
                  AND e.active=1 AND e.expires>=? AND v.severity>=?
                  ORDER BY v.severity DESC,v.created DESC LIMIT 20''',
                  (owner,project,int(time.time()),min_severity)).fetchall()
        return [dict(r) for r in rows]

    def focus(self, project: str, limit=3):
        """Attention via existing authorized goals + observed deviations, no new agent goals."""
        project, owner = self._scope(project)
        if type(limit) is not int or not 1 <= limit <= 6: raise ValueError('limit 1..6')
        with self.brain.connection() as db:
            paused = self._paused(db,project,owner)
            # Find first unfinished step per goal; blocked step prevents implicit retry.
            rows=db.execute('''SELECT g.id goal_id,g.title,g.desired_result,g.priority,
                  s.id step_id,s.instruction,s.attempts,s.status,s.ordinal
                  FROM goals g JOIN steps s ON s.goal_id=g.id
                  WHERE g.owner=? AND g.project=? AND g.state='active'
                  AND s.status IN ('pending','blocked')
                  ORDER BY g.created ASC,s.ordinal ASC''',(owner,project)).fetchall()
            anomalies=db.execute('''SELECT a.id,e.subject,e.expected,v.value,v.source,v.severity
                  FROM cognitive_anomalies a
                  JOIN cognitive_events v ON v.id=a.event_id
                  JOIN cognitive_expectations e ON e.id=a.expectation_id
                  WHERE a.owner=? AND a.project=? AND a.status='open'
                  AND e.active=1 AND e.expires>=?
                  ORDER BY v.severity DESC,v.created DESC LIMIT 8''',
                  (owner,project,int(time.time()))).fetchall()
        chosen=[]; seen=set()
        for r in rows:
            if r['goal_id'] in seen: continue
            seen.add(r['goal_id'])
            if r['status']!='pending': continue
            # Priority is assigned by user; scoring is an explainable heuristic, not a brain.
            score=(6-r['priority'])*20-min(r['attempts'],5)*5
            chosen.append({'type':'existing_goal_step','goal_id':r['goal_id'],
                           'step_id':r['step_id'],'goal':r['title'],
                           'instruction':r['instruction'],'score':score,
                           'rationale':'User-prioritized unfinished step'})
        for a in anomalies:
            chosen.append({'type':'observation_mismatch','anomaly_id':a['id'],
                           'subject':a['subject'],'expected':a['expected'],
                           'observed':a['value'],'source':a['source'],'severity':a['severity'],
                           'score':60+a['severity']*6,
                           'rationale':'Actual observation differs from configured expectation; investigate only'})
        chosen.sort(key=lambda x:(-x['score'],x['type'],x.get('step_id','')))
        return {'paused':paused,'candidates':chosen[:limit] if not paused else [],
                'note':'Attention proposals only; no automatic execution, Claude calls, or access escalation.'}

    def consolidate(self, project: str):
        """Offline reflection: detect duplicate proposals; never self-verify facts."""
        project, owner = self._scope(project)
        with self.brain.connection() as db:
            proposed=db.execute('SELECT id,title,content FROM memory WHERE owner=? AND project=? '
                                'AND status=? ORDER BY updated DESC LIMIT 500',
                                (owner,project,'proposed')).fetchall()
            episodes=db.execute('SELECT task_type,outcome,COUNT(*) count FROM episodes '
                                'WHERE owner=? AND project=? AND verified=1 GROUP BY task_type,outcome '
                                'ORDER BY task_type,outcome LIMIT 30',
                                (owner,project)).fetchall()
        buckets={}
        for item in proposed:
            digest=hashlib.sha256((item['title'].strip().casefold()+'\0'+
                                   item['content'].strip().casefold()).encode('utf-8')).hexdigest()
            buckets.setdefault(digest,[]).append(item['id'])
        doubles=[ids for ids in buckets.values() if len(ids)>1]
        return {'duplicate_proposal_groups':doubles[:12],
                'verified_episode_groups':[dict(row) for row in episodes],
                'note':'Advisory consolidation only: no AI summary, no automatic memory confirmation/deletion.'}

    def cycle(self, project: str):
        """Autonomic tick; record no unsolicited instructions or actions."""
        status=self.health(project)
        if status['paused']:
            return {'health':status,'focus':{'candidates':[]},'reflection':None,
                    'note':'Paused: no improvement cycle or outbound work'}
        return {'health':status,'focus':self.focus(project),
                'reflection':self.consolidate(project),
                'verified_failure_suggestions':self.brain.tick(project)['new_suggestions'],
                'note':'No Claude tokens consumed by this local loop.'}
