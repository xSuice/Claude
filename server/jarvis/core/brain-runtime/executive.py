#!/usr/bin/env python3
"""V9 executive control: carries authorized goal steps through act -> check -> learn.

* Plans are the existing goals/steps (brain_create_goal). A step becomes executable only
  when it is bound to an admin-allowlisted action plus an independent local check action
  (runner.py). Claude may bind via MCP but cannot invent commands.
* Every transition is persisted with a lease, so a crash or reboot never loses finished
  work: expired leases of idempotent actions are resumed, others are blocked for review.
* A step is 'verified' only if its check action passes - never on the model's claim.
* Bounded: steps per run, local runs per day, attempts per step; pause is respected.
* Claude actions (claude_template) are only queued in the existing autonomy queue with
  its own opt-in, daily cap and cost limits; this module never starts Claude itself.
* Outcomes are logged as verified episodes, so Brain.tick() learns recurring failures.
Intended to run from the supervisor / a systemd timer, e.g. every 15 minutes.
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
from cognitive_loop import CognitiveLoop  # noqa: E402
import runner  # noqa: E402
from orders import Orders, killed  # noqa: E402

STATES = ('ready', 'running', 'waiting', 'done', 'failed', 'interrupted', 'awaiting_approval')
SCHEMA = f'''
CREATE TABLE IF NOT EXISTS exec_bindings(
    step_id TEXT PRIMARY KEY, owner TEXT NOT NULL, project TEXT NOT NULL,
    action TEXT NOT NULL, check_action TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'ready' CHECK(state IN {STATES}),
    lease_until INTEGER, job_id TEXT, last_exit INTEGER, last_tail TEXT, updated INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS exec_runs(
    id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL, step_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('action','check','claude')), action TEXT NOT NULL,
    exit INTEGER, ms INTEGER, output_sha256 TEXT, tail TEXT, started INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS exec_runs_day ON exec_runs(owner, started);
'''


class Executive:
    def __init__(self, brain: Brain, actions_cfg: dict, workspace: Path, autonomy_cfg: dict | None = None,
                 helpers=None, route=None):
        self.brain, self.loop = brain, CognitiveLoop(brain)
        self.cfg = runner.validate(actions_cfg)
        self.actions, self.limits = self.cfg['actions'], self.cfg['limits']
        self.workspace = Path(workspace).expanduser().resolve(strict=True)
        self.autonomy = autonomy_cfg
        with brain.connection(True) as db:
            old = db.execute("SELECT sql FROM sqlite_master WHERE name='exec_bindings'").fetchone()
            if old and 'awaiting_approval' not in old[0]:   # V9 -> V10: widen the state CHECK
                db.execute('ALTER TABLE exec_bindings RENAME TO exec_bindings_v9')
                db.executescript(SCHEMA)
                db.execute('INSERT INTO exec_bindings SELECT * FROM exec_bindings_v9')
                db.execute('DROP TABLE exec_bindings_v9')
            db.executescript(SCHEMA)
        self.hide = [str(brain.db_path.parent)]
        self.orders = Orders(brain)
        self.defer_remote = False  # V11: set by the daemon in conserve/protect mode
        self.helpers, self.route = helpers, route  # V11: provider_adapter.HelperClient, route_policy.RoutePolicy
        # AP-4: lazy provider registry (fail-closed)
        self._provider_registry = None
        try:
            from provider_registry import ProviderRegistry
            self._provider_registry = ProviderRegistry()
        except Exception:
            pass  # registry unavailable -> callers fall back to raw strings

    # ---------- planning (MCP / CLI) ----------
    def bind(self, project: str, step_id: str, action: str, check: str, by: str = 'admin') -> dict:
        """by='mcp': the model asked. Then only actions (and checks) marked "auto": true become
        ready at once; anything else waits for `approve` by the operator (prompt-injection guard)."""
        if by not in ('admin', 'mcp'):
            raise ValueError('by must be admin or mcp')
        project = self.brain._project(project)
        if action not in self.actions:
            raise ValueError('unknown action (must be in the admin allowlist)')
        if check not in self.actions or 'claude_template' in self.actions[check] or 'helper_task' in self.actions[check]:
            raise ValueError('check must be a local allowlisted action')
        now = int(time.time())
        with self.brain.connection(True) as db:
            row = db.execute('SELECT s.status,g.owner,g.project,g.state FROM steps s JOIN goals g ON g.id=s.goal_id '
                             'WHERE s.id=?', (step_id,)).fetchone()
            if not row or row['owner'] != self.brain.identity or row['project'] != project:
                raise PermissionError('step not allowed')
            if row['status'] != 'pending' or row['state'] != 'active':
                raise ValueError('only pending steps of active goals can be bound')
            cur = db.execute('SELECT state FROM exec_bindings WHERE step_id=?', (step_id,)).fetchone()
            if cur and cur['state'] in ('running', 'waiting'):
                raise ValueError('step is currently executing')
            auto = all(self.actions[n].get('auto') for n in (action, check))
            privileged = any(self.actions[n].get('risk') == 'privileged' for n in (action, check))
            # V10.1: privileged actions always need an explicit `approve`, whoever binds them
            state = 'awaiting_approval' if privileged or (by != 'admin' and not auto) else 'ready'
            db.execute('INSERT INTO exec_bindings(step_id,owner,project,action,check_action,state,updated) '
                       'VALUES(?,?,?,?,?,?,?) ON CONFLICT(step_id) DO UPDATE SET action=excluded.action,'
                       "check_action=excluded.check_action,state=excluded.state,lease_until=NULL,job_id=NULL,"
                       'updated=excluded.updated', (step_id, self.brain.identity, project, action, check, state, now))
        return {'step_id': step_id, 'action': action, 'check': check, 'state': state,
                'note': 'Executed later by the local executive; verified only if the check passes.'}

    def approve(self, project: str, step_id: str) -> dict:
        """Operator CLI only (never exposed via MCP)."""
        project = self.brain._project(project)
        with self.brain.connection(True) as db:
            cur = db.execute("UPDATE exec_bindings SET state='ready',updated=? WHERE step_id=? AND owner=? "
                             "AND project=? AND state='awaiting_approval'",
                             (int(time.time()), step_id, self.brain.identity, project))
            if cur.rowcount != 1:
                raise ValueError('no binding awaiting approval for this step')
        return {'step_id': step_id, 'state': 'ready'}

    def _run(self, spec):
        return runner.run(spec, self.workspace, {'hide': self.hide} if spec.get('sandbox') else None)

    # ---------- execution ----------
    def _runs_today(self, db, now):
        return db.execute('SELECT COUNT(*) FROM exec_runs WHERE owner=? AND started>=? AND kind!=?',
                          (self.brain.identity, now - 86400, 'claude')).fetchone()[0]

    def _journal(self, step_id, kind, action, res, now):
        with self.brain.connection(True) as db:
            db.execute('INSERT INTO exec_runs(owner,step_id,kind,action,exit,ms,output_sha256,tail,started) '
                       'VALUES(?,?,?,?,?,?,?,?,?)', (self.brain.identity, step_id, kind, action, res.get('exit'),
                                                     res.get('ms'), res.get('output_sha256'), res.get('tail'), now))

    def _finish(self, b, ok: bool, res: dict, now: int) -> str:
        """Persist check outcome: verified / retry / blocked, episode for learning, goal completion."""
        with self.brain.connection(True) as db:
            step = db.execute('SELECT s.*,g.project,g.id gid FROM steps s JOIN goals g ON g.id=s.goal_id '
                              'WHERE s.id=?', (b['step_id'],)).fetchone()
            attempts = step['attempts'] + 1
            if ok:
                db.execute("UPDATE steps SET status='verified',attempts=?,outcome=?,updated=? WHERE id=?",
                           (attempts, f"check {b['check_action']} passed", now, b['step_id']))
                state = 'done'
            elif attempts >= self.limits['max_attempts']:
                db.execute("UPDATE steps SET status='blocked',attempts=?,outcome=?,updated=? WHERE id=?",
                           (attempts, f"check {b['check_action']} failed {attempts}x (exit {res.get('exit')})",
                            now, b['step_id']))
                state = 'failed'
            else:
                db.execute('UPDATE steps SET attempts=?,updated=? WHERE id=?', (attempts, now, b['step_id']))
                state = 'ready'  # retried in a later run, never in a tight loop
            db.execute('UPDATE exec_bindings SET state=?,lease_until=NULL,last_exit=?,last_tail=?,updated=? '
                       'WHERE step_id=?', (state, res.get('exit'), res.get('tail', '')[-300:], now, b['step_id']))
            db.execute("INSERT INTO episodes(id,owner,project,task_type,summary,outcome,evidence,model_calls,"
                       "elapsed_ms,verified,created) VALUES(lower(hex(randomblob(16))),?,?,?,?,?,?,0,?,1,?)",
                       (self.brain.identity, step['project'], f"action:{b['action']}"[:60],
                        step['instruction'][:500], 'success' if ok else 'failure',
                        f"check {b['check_action']} exit {res.get('exit')} sha {res.get('output_sha256')}",
                        res.get('ms'), now))
            left = db.execute("SELECT COUNT(*) FROM steps WHERE goal_id=? AND status!='verified'",
                              (step['gid'],)).fetchone()[0]
            if left == 0:
                db.execute("UPDATE goals SET state='completed' WHERE id=?", (step['gid'],))
        return state

    def reconcile(self, now: int) -> list[dict]:
        """After a crash/reboot: idempotent work is resumed. For non-idempotent work the
        independent check decides: effect already there -> verified (no work lost, no re-run),
        otherwise blocked for human review. Never re-runs a non-idempotent action."""
        out = []
        with self.brain.connection(True) as db:
            stale = [dict(b) for b in db.execute("SELECT * FROM exec_bindings WHERE owner=? AND state='running' "
                                                 "AND lease_until<?", (self.brain.identity, now))]
            for b in stale:
                if self.actions.get(b['action'], {}).get('idempotent'):
                    db.execute("UPDATE exec_bindings SET state='ready',lease_until=NULL,updated=? WHERE step_id=?",
                               (now, b['step_id']))
                else:
                    db.execute("UPDATE exec_bindings SET state='interrupted',lease_until=NULL,updated=? "
                               "WHERE step_id=?", (now, b['step_id']))
        for b in stale:
            if self.actions.get(b['action'], {}).get('idempotent'):
                out.append({'step_id': b['step_id'], 'resumed': True}); continue
            chk = self.actions.get(b['check_action'])
            res = self._run(chk) if chk and 'claude_template' not in chk else {'ok': False, 'exit': None}
            self._journal(b['step_id'], 'check', b['check_action'], res, now)
            if res['ok']:
                state = self._finish(b, True, res, now)
            else:
                with self.brain.connection(True) as db:
                    db.execute("UPDATE steps SET status='blocked',outcome=?,updated=? WHERE id=?",
                               ('interrupted while running; check failed; not idempotent - review before retry',
                                now, b['step_id']))
                state = 'interrupted'
            out.append({'step_id': b['step_id'], 'resumed': False, 'state': state})
        return out

    def _candidates(self, project: str):
        with self.brain.connection() as db:
            rows = db.execute('''SELECT g.id gid,g.priority,s.id step_id,s.status,b.state bstate
                FROM goals g JOIN steps s ON s.goal_id=g.id LEFT JOIN exec_bindings b ON b.step_id=s.id
                WHERE g.owner=? AND g.project=? AND g.state='active' AND s.status IN ('pending','blocked')
                ORDER BY g.priority ASC,g.created ASC,s.ordinal ASC''', (self.brain.identity, project)).fetchall()
        seen, ready, unbound = set(), [], []
        for r in rows:  # only the first unfinished step per goal = ordinal dependencies
            if r['gid'] in seen:
                continue
            seen.add(r['gid'])
            if r['status'] != 'pending':
                continue
            if r['bstate'] == 'ready':
                ready.append(r['step_id'])
            elif r['bstate'] is None:
                unbound.append(r['step_id'])
        return ready, unbound

    def run_once(self, project: str, now: int | None = None) -> dict:
        now = int(time.time()) if now is None else now
        if killed(self.brain):
            return {'killed': True, 'executed': [], 'reconciled': []}
        if self.loop.health(project)['paused']:
            return {'paused': True}
        expired = self.orders.expire(now)
        report = {'expired': expired, 'reconciled': self.reconcile(now), 'executed': [], 'waiting': [], 'skipped': []}
        report['waiting'] = self._poll_claude(now)
        ready, unbound = self._candidates(project)
        report['needs_binding'] = unbound
        for step_id in ready[:self.limits['max_steps_per_run']]:
            with self.brain.connection(True) as db:
                if self._runs_today(db, now) + 2 > self.limits['max_local_runs_per_day']:
                    report['skipped'].append({'step_id': step_id, 'reason': 'daily local run limit'}); break
                b = db.execute('SELECT * FROM exec_bindings WHERE step_id=?', (step_id,)).fetchone()
                spec = self.actions.get(b['action']); chk = self.actions.get(b['check_action'])
                if spec is None or chk is None or 'claude_template' in chk:
                    report['skipped'].append({'step_id': step_id, 'reason': 'action no longer allowlisted'})
                    continue
                lease = now + spec.get('timeout', 300) + chk.get('timeout', 300) + 120
                cur = db.execute("UPDATE exec_bindings SET state='running',lease_until=?,updated=? "
                                 "WHERE step_id=? AND state='ready'", (lease, now, step_id))
                if cur.rowcount != 1:
                    continue  # another worker took it
                b = dict(b)
            if 'claude_template' in spec:
                report['executed'].append(self._queue_claude(b, spec, now)); continue
            if 'helper_task' in spec:
                report['executed'].append(self._run_helper(b, spec, chk, now)); continue
            act = self._run(spec)
            self._journal(step_id, 'action', b['action'], act, now)
            res = self._run(chk) if act['ok'] else act
            if act['ok']:
                self._journal(step_id, 'check', b['check_action'], res, now)
            state = self._finish(b, act['ok'] and res['ok'], res, now)
            report['executed'].append({'step_id': step_id, 'action_exit': act['exit'],
                                       'check_exit': res['exit'] if act['ok'] else None, 'state': state})
        report['claude_calls_started'] = 0
        return report

    # ---------- Claude via the existing bounded queue ----------
    def _queue_claude(self, b, spec, now):
        if self.defer_remote:
            with self.brain.connection(True) as db:
                db.execute("UPDATE exec_bindings SET state='ready',lease_until=NULL,updated=? WHERE step_id=?",
                           (now, b['step_id']))
            return {'step_id': b['step_id'], 'state': 'ready', 'reason': 'deferred: resources short'}
        with self.brain.connection() as db:
            gid = db.execute('SELECT goal_id FROM steps WHERE id=?', (b['step_id'],)).fetchone()[0]
        if self.autonomy and self.autonomy.get('enabled') and not self.orders.charge_claude(gid):
            res = {'exit': None, 'ok': False, 'tail': 'claude budget of this order exhausted'}
            self._journal(b['step_id'], 'claude', spec['claude_template'], res, now)
            with self.brain.connection(True) as db:
                db.execute("UPDATE steps SET status='blocked',outcome=?,updated=? WHERE id=?",
                           ('claude budget of this order exhausted', now, b['step_id']))
                db.execute("UPDATE exec_bindings SET state='failed',lease_until=NULL,updated=? WHERE step_id=?",
                           (now, b['step_id']))
            return {'step_id': b['step_id'], 'state': 'failed', 'reason': 'claude budget exhausted'}
        if not self.autonomy or not self.autonomy.get('enabled'):
            with self.brain.connection(True) as db:
                db.execute("UPDATE exec_bindings SET state='ready',lease_until=NULL,updated=? WHERE step_id=?",
                           (now, b['step_id']))
            return {'step_id': b['step_id'], 'state': 'ready', 'reason': 'claude queue disabled (no cost)'}
        from autonomy import Queue
        meta = self.orders.meta(gid) or {}
        job = Queue(self.autonomy['db_path']).enqueue(self.autonomy, self.brain.identity, b['project'],
                                                      spec['claude_template'], str(self.workspace),
                                                      topic=meta.get('topic'))
        with self.brain.connection(True) as db:
            db.execute("UPDATE exec_bindings SET state='waiting',job_id=?,lease_until=NULL,updated=? WHERE step_id=?",
                       (job, now, b['step_id']))
        self._journal(b['step_id'], 'claude', spec['claude_template'], {}, now)
        return {'step_id': b['step_id'], 'state': 'waiting', 'job_id': job}

    def _park(self, b, now, why):
        with self.brain.connection(True) as db:
            db.execute("UPDATE steps SET status='blocked',outcome=?,updated=? WHERE id=?", (f'parked: {why}', now, b['step_id']))
            db.execute("UPDATE exec_bindings SET state='failed',lease_until=NULL,updated=? WHERE step_id=?", (now, b['step_id']))
        return {'step_id': b['step_id'], 'state': 'parked', 'reason': why}

    def _run_helper(self, b, spec, chk, now):
        """V11: route -> eligible helper(s) -> independent local check; fallback Claude queue -> park.
        Helper output is stored only as an unconfirmed hypothesis and never executed."""
        from provider_adapter import Refused, classify
        if self.defer_remote:
            with self.brain.connection(True) as db:
                db.execute("UPDATE exec_bindings SET state='ready',lease_until=NULL,updated=? WHERE step_id=?", (now, b['step_id']))
            return {'step_id': b['step_id'], 'state': 'ready', 'reason': 'deferred: resources short'}
        with self.brain.connection() as db:
            gid, instr = db.execute('SELECT goal_id, instruction FROM steps WHERE id=?', (b['step_id'],)).fetchone()
        meta = self.orders.meta(gid) or {}
        payload = instr
        if meta.get('topic'):
            f = (self.workspace / meta['topic']).resolve()
            if self.workspace in f.parents and f.is_file():
                payload = f.read_text(encoding='utf-8', errors='replace')[:16000]
        cls = classify(payload, meta.get('data_class', 'internal'))
        req = {'task_type': spec['helper_task'], 'risk': meta.get('risk', 'reversible'), 'data_class': cls,
               'size_chars': len(payload), 'has_procedure': False,
               'fallback': 'claude' if spec.get('fallback_template') else None}
        decision = self.route.decide(req, b['project'], gid) if self.route else {'executed': 'human', 'mode': 'none'}
        tried, target = [], decision['executed']
        if target.startswith('helper:') and self.helpers is not None:
            from helper_verify import DEFAULTS, PROMPTS, verify
            vspec = spec.get('verify') or DEFAULTS.get(spec['helper_task'])
            if not vspec:
                return {**self._park(b, now, f"helper task {spec['helper_task']} has no answer verifier"), 'tried': tried}
            pre = self._run(chk)                    # infrastructure precondition (e.g. packet exists) - NOT quality
            self._journal(b['step_id'], 'check', b['check_action'], pre, now)
            if not pre['ok']:
                return {**self._park(b, now, f"precondition {b['check_action']} failed"), 'tried': tried}
            prompt = PROMPTS.get(vspec.get('type'), '') + payload
            order = [target.split(':', 1)[1]] + [p for p in getattr(self.route, 'order', []) if p != target.split(':', 1)[1]]
            for prov in order:
                if not self.orders.charge_helper(gid):
                    tried.append(f'{prov}: helper budget exhausted'); break
                try:
                    r = self.helpers.call(prov, spec['helper_task'], prompt, project=b['project'],
                                          declared_class=meta.get('data_class', 'internal'), order_id=gid)
                except Refused as e:
                    tried.append(f'{prov}: {e}'); continue
                ok, why = verify(vspec, r['text'], payload, r['suspicious'])
                self.helpers.mark_call(r['call_id'], ok, why)
                self._journal(b['step_id'], 'check', f'verify:{prov}:{spec["helper_task"]}'[:60],
                              {'ok': ok, 'exit': 0 if ok else 1, 'tail': why, 'ms': r['latency_ms']}, now)
                self.brain.propose(b['project'], f"Helfer {prov}: {spec['helper_task']}"[:120], (r['text'] or '(leere Antwort)')[:4000],
                                   f'helper {prov} order {gid} ' + ('grounded' if ok else f'UNVERIFIED: {why}')
                                   + (' SUSPICIOUS' if r['suspicious'] else ''), 'hypothesis')
                if not ok:
                    tried.append(f'{prov}: answer rejected ({why})'); continue
                state = self._finish(b, True, {**pre, 'tail': why}, now)
                return {'step_id': b['step_id'], 'state': state, 'helper': prov, 'tried': tried,
                        'verification': why, 'route': decision.get('mode')}
            target = 'claude'
        if target.startswith('claude') and spec.get('fallback_template') and self.autonomy and self.autonomy.get('enabled'):
            out = self._queue_claude(b, {'claude_template': spec['fallback_template']}, now)
            return {**out, 'tried': tried, 'route': decision.get('mode')}
        return {**self._park(b, now, 'no permitted helper or Claude route' + (f' ({"; ".join(tried)})' if tried else '')),
                'tried': tried}

    def _poll_claude(self, now):
        if not self.autonomy:
            return []
        from autonomy import Queue
        q = Queue(self.autonomy['db_path']); out = []
        with self.brain.connection() as db:
            waiting = [dict(r) for r in db.execute("SELECT * FROM exec_bindings WHERE owner=? AND state='waiting'",
                                                   (self.brain.identity,))]
        for b in waiting:
            with q.connect() as c:
                job = c.execute('SELECT status,exit_code FROM jobs WHERE id=?', (b['job_id'],)).fetchone()
            if job is None or job['status'] in ('queued', 'running'):
                out.append({'step_id': b['step_id'], 'job': job['status'] if job else 'missing'}); continue
            chk = self.actions.get(b['check_action'])
            res = self._run(chk) if job['status'] == 'done' and chk else \
                {'exit': job['exit_code'], 'ok': False, 'tail': 'claude job failed'}
            self._journal(b['step_id'], 'check', b['check_action'], res, now)
            out.append({'step_id': b['step_id'], 'state': self._finish(b, res['ok'], res, now)})
        return out

    def status(self, project: str) -> dict:
        project = self.brain._project(project)
        with self.brain.connection() as db:
            rows = [dict(r) for r in db.execute(
                'SELECT b.step_id,b.action,b.check_action,b.state,b.last_exit,s.attempts,s.status,g.title '
                'FROM exec_bindings b JOIN steps s ON s.id=b.step_id JOIN goals g ON g.id=s.goal_id '
                'WHERE b.owner=? AND b.project=? ORDER BY b.updated DESC LIMIT 30', (self.brain.identity, project))]
            today = self._runs_today(db, int(time.time()))
        return {'bindings': rows, 'local_runs_24h': today, 'limits': self.limits}


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--config', type=Path, required=True, help='brain config')
    p.add_argument('--actions', type=Path, required=True)
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--autonomy-config', type=Path, help='optional existing V6 queue config')
    p.add_argument('--project', required=True)
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('run-once'); sub.add_parser('status')
    b = sub.add_parser('bind'); b.add_argument('step_id'); b.add_argument('action'); b.add_argument('check')
    sub.add_parser('approve').add_argument('step_id')
    a = p.parse_args()
    try:
        conf = json.loads(a.config.resolve(strict=True).read_text(encoding='utf-8'))
        db = Path(conf['state_db']).expanduser()
        if not db.is_absolute(): db = (a.config.resolve().parent / db).resolve()
        auto = None
        if a.autonomy_config:
            from autonomy import load_config
            auto = load_config(a.autonomy_config)
        ex = Executive(Brain(db, conf['identity'], set(conf['allowed_projects'])),
                       runner.load_actions(a.actions), a.workspace, auto)
        if a.cmd == 'run-once': out = ex.run_once(a.project)
        elif a.cmd == 'status': out = ex.status(a.project)
        elif a.cmd == 'approve': out = ex.approve(a.project, a.step_id)
        else: out = ex.bind(a.project, a.step_id, a.action, a.check)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    except (OSError, ValueError, KeyError, PermissionError) as e:
        print(f'ERROR: {type(e).__name__}: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
