#!/usr/bin/env python3
"""V8 experience learning from real Claude Code sessions - zero extra model calls.

`hook`   Claude Code Stop hook: reads the hook JSON on stdin, parses the session
         transcript locally (model, effort, requests, tokens incl. cache, tool uses,
         duration) and upserts one row per session. Never blocks Claude: always exit 0.
`rate`   A human marks a session success/failure (+ task type). Only rated runs count.
`stats`  Per task type and model/effort: success rate and median tokens per success.
`export` Writes router-experience.json for the MA Auto Router (read-only input for it;
         the router keeps its own decision logic - no second router).

Settings snippet (~/.claude/settings.json):
  "hooks": {"Stop": [{"hooks": [{"type": "command",
     "command": "python3 /PATH/brain-runtime/experience.py hook --config /PATH/brain.json"}]}]}
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAX_TRANSCRIPT = 200 * 1024 * 1024
OUTCOMES = ('success', 'failure')
SCHEMA = '''CREATE TABLE IF NOT EXISTS experience_runs(
    session_id TEXT NOT NULL, owner TEXT NOT NULL, project TEXT NOT NULL,
    models TEXT NOT NULL, main_model TEXT, effort TEXT, requests INTEGER NOT NULL,
    input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL,
    cache_read_tokens INTEGER NOT NULL, cache_write_tokens INTEGER NOT NULL,
    tool_uses INTEGER NOT NULL, user_turns INTEGER NOT NULL, duration_s INTEGER,
    updated INTEGER NOT NULL, outcome TEXT NOT NULL DEFAULT 'unrated'
        CHECK(outcome IN ('unrated','success','failure')),
    task_type TEXT, rated INTEGER, note TEXT,
    PRIMARY KEY(owner, session_id))'''
TASKS = '''CREATE TABLE IF NOT EXISTS experience_tasks(
    id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL, session_id TEXT NOT NULL,
    project TEXT NOT NULL, task_type TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK(outcome IN ('success','failure')),
    granularity TEXT NOT NULL CHECK(granularity IN ('task','session')),
    turn_from INTEGER, turn_to INTEGER, main_model TEXT, effort TEXT, requests INTEGER,
    input_tokens INTEGER, output_tokens INTEGER, cache_read_tokens INTEGER,
    cache_write_tokens INTEGER, tool_uses INTEGER, duration_s INTEGER,
    rework_minutes INTEGER, rated INTEGER NOT NULL, note TEXT,
    UNIQUE(owner, session_id, turn_from, turn_to))'''
SUFFICIENT_RUNS = 10  # per task_type+model+effort, task granularity only


def _ts(value):
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).timestamp()
    except (ValueError, TypeError):
        return None


def parse_transcript(path: Path, turns: tuple[int, int] | None = None) -> dict:
    """Aggregate one session, or (V8.1) only user turns lo..hi (1-based) of it, so one
    task inside a multi-task session can be measured on its own. Usage repeats on every
    content block of a request, so it is counted once per requestId (last line wins)."""
    per_request, models, efforts = {}, {}, {}
    tool_uses = user_turns = 0
    first = last = None
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not isinstance(d, dict):
                continue
            msg = d.get('message') if isinstance(d.get('message'), dict) else {}
            if d.get('type') == 'user' and not d.get('isSidechain'):
                content = msg.get('content')
                if isinstance(content, str) or (isinstance(content, list) and any(
                        isinstance(c, dict) and c.get('type') == 'text' for c in content)):
                    user_turns += 1
            if turns and not turns[0] <= user_turns <= turns[1]:
                continue
            t = _ts(d.get('timestamp'))
            if t:
                first = t if first is None else min(first, t)
                last = t if last is None else max(last, t)
            if d.get('type') != 'assistant':
                continue
            for c in msg.get('content') or []:
                if isinstance(c, dict) and c.get('type') == 'tool_use':
                    tool_uses += 1
            usage = msg.get('usage') if isinstance(msg.get('usage'), dict) else None
            rid = d.get('requestId') or msg.get('id')
            if usage and rid:
                per_request[rid] = (msg.get('model') or 'unknown', usage)
            if d.get('effort'):
                efforts[str(d['effort'])] = efforts.get(str(d['effort']), 0) + 1
    tot = dict(input_tokens=0, output_tokens=0, cache_read_tokens=0, cache_write_tokens=0)
    for model, u in per_request.values():
        models[model] = models.get(model, 0) + 1
        tot['input_tokens'] += int(u.get('input_tokens') or 0)
        tot['output_tokens'] += int(u.get('output_tokens') or 0)
        tot['cache_read_tokens'] += int(u.get('cache_read_input_tokens') or 0)
        tot['cache_write_tokens'] += int(u.get('cache_creation_input_tokens') or 0)
    main = max(models, key=models.get) if models else None
    return {'models': models, 'main_model': main,
            'effort': max(efforts, key=efforts.get) if efforts else None,
            'requests': len(per_request), 'tool_uses': tool_uses, 'user_turns': user_turns,
            'duration_s': int(last - first) if first and last else None, **tot}


class Experience:
    def __init__(self, db: Path, identity: str, projects: set[str], default_project: str,
                 projects_by_path: dict | None = None, transcript_root: Path | None = None):
        self.db, self.identity, self.projects = Path(db), identity, projects
        if default_project not in projects:
            raise ValueError('default_project must be an allowed project')
        self.default = default_project
        self.by_path = {str(Path(k).expanduser().resolve()): v for k, v in (projects_by_path or {}).items()
                        if v in projects}
        self.root = Path(transcript_root or Path.home() / '.claude' / 'projects').expanduser().resolve()
        import sqlite3
        self._sqlite = sqlite3
        with self._conn() as c:
            c.execute(SCHEMA)
            c.execute(TASKS)
            cols = {r['name'] for r in c.execute('PRAGMA table_info(experience_runs)')}
            if 'transcript' not in cols:
                c.execute('ALTER TABLE experience_runs ADD COLUMN transcript TEXT')

    @contextmanager
    def _conn(self):
        c = self._sqlite.connect(str(self.db), timeout=5)
        c.row_factory = self._sqlite.Row
        c.execute('PRAGMA busy_timeout=5000')
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    def project_for(self, cwd: str | None) -> str:
        if cwd:
            p = Path(cwd).expanduser().resolve()
            for root, proj in sorted(self.by_path.items(), key=lambda x: -len(x[0])):
                if p == Path(root) or Path(root) in p.parents:
                    return proj
        return self.default

    def record(self, hook: dict) -> dict:
        if hook.get('stop_hook_active'):
            return {'skipped': 'stop_hook_active'}
        sid, tp = hook.get('session_id'), hook.get('transcript_path')
        if not isinstance(sid, str) or not 8 <= len(sid) <= 80 or not isinstance(tp, str):
            raise ValueError('hook input lacks session_id/transcript_path')
        path = Path(tp).expanduser().resolve(strict=True)
        if self.root not in path.parents or path.suffix != '.jsonl' or path.stat().st_size > MAX_TRANSCRIPT:
            raise PermissionError('transcript outside the Claude projects folder')
        agg = parse_transcript(path)
        project = self.project_for(hook.get('cwd'))
        with self._conn() as c:
            c.execute('''INSERT INTO experience_runs(session_id,owner,project,models,main_model,effort,
                requests,input_tokens,output_tokens,cache_read_tokens,cache_write_tokens,tool_uses,
                user_turns,duration_s,updated,transcript) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(owner,session_id) DO UPDATE SET models=excluded.models,
                main_model=excluded.main_model,effort=excluded.effort,requests=excluded.requests,
                input_tokens=excluded.input_tokens,output_tokens=excluded.output_tokens,
                cache_read_tokens=excluded.cache_read_tokens,cache_write_tokens=excluded.cache_write_tokens,
                tool_uses=excluded.tool_uses,user_turns=excluded.user_turns,
                duration_s=excluded.duration_s,updated=excluded.updated,transcript=excluded.transcript''',
                (sid, self.identity, project, json.dumps(agg['models']), agg['main_model'], agg['effort'],
                 agg['requests'], agg['input_tokens'], agg['output_tokens'], agg['cache_read_tokens'],
                 agg['cache_write_tokens'], agg['tool_uses'], agg['user_turns'], agg['duration_s'],
                 int(time.time()), str(path)))
        return {'session_id': sid, 'project': project, **{k: agg[k] for k in ('main_model', 'requests')}}

    def rate(self, session_id: str, outcome: str, task_type: str, note: str = '',
             turns: tuple[int, int] | None = None, rework_minutes: int | None = None) -> dict:
        """Human rating. With `turns` (lo, hi) only that part of the session is measured
        (granularity 'task'); without it the whole session counts (granularity 'session')."""
        if outcome not in OUTCOMES:
            raise ValueError('outcome must be success or failure')
        if not isinstance(task_type, str) or not 1 <= len(task_type) <= 40 or not task_type.replace('-', '').isalnum():
            raise ValueError('task_type: 1..40 letters/digits/-')
        if rework_minutes is not None and (type(rework_minutes) is not int or not 0 <= rework_minutes <= 10000):
            raise ValueError('rework_minutes 0..10000')
        if not isinstance(session_id, str) or len(session_id) < 8:
            raise ValueError('session id (or a prefix of >= 8 chars) required')
        with self._conn() as c:
            rows = c.execute('SELECT * FROM experience_runs WHERE owner=? AND (session_id=? OR session_id LIKE ?)',
                             (self.identity, session_id, session_id.replace('%', '') + '%')).fetchall()
            if len(rows) != 1:
                raise ValueError('session not found or prefix ambiguous')
            run = dict(rows[0])
            if turns:
                lo, hi = turns
                if type(lo) is not int or type(hi) is not int or not 1 <= lo <= hi <= run['user_turns']:
                    raise ValueError(f"turns must be within 1..{run['user_turns']}")
                tp = Path(run.get('transcript') or '')
                if not tp.is_file() or self.root not in tp.resolve().parents:
                    raise ValueError('transcript no longer available; rate the whole session instead')
                agg = parse_transcript(tp, (lo, hi))
                gran = 'task'
            else:
                lo = hi = None
                agg = {k: run[k] for k in ('main_model', 'effort', 'requests', 'input_tokens', 'output_tokens',
                                           'cache_read_tokens', 'cache_write_tokens', 'tool_uses', 'duration_s')}
                gran = 'session'
            c.execute('''INSERT INTO experience_tasks(owner,session_id,project,task_type,outcome,granularity,
                turn_from,turn_to,main_model,effort,requests,input_tokens,output_tokens,cache_read_tokens,
                cache_write_tokens,tool_uses,duration_s,rework_minutes,rated,note)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(owner,session_id,turn_from,turn_to) DO UPDATE SET outcome=excluded.outcome,
                task_type=excluded.task_type,rework_minutes=excluded.rework_minutes,note=excluded.note,
                rated=excluded.rated''',
                (self.identity, run['session_id'], run['project'], task_type.lower(), outcome, gran, lo, hi,
                 agg['main_model'], agg['effort'], agg['requests'], agg['input_tokens'], agg['output_tokens'],
                 agg['cache_read_tokens'], agg['cache_write_tokens'], agg['tool_uses'], agg['duration_s'],
                 rework_minutes, int(time.time()), note[:300]))
            c.execute("UPDATE experience_runs SET outcome=?,task_type=?,rated=?,note=? WHERE owner=? AND session_id=?",
                      (outcome, task_type.lower(), int(time.time()), note[:300], self.identity, run['session_id']))
        return {'session': run['session_id'], 'outcome': outcome, 'task_type': task_type.lower(),
                'granularity': gran, 'turns': [lo, hi] if turns else None}

    def unrated(self, limit=10) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute('''SELECT session_id,project,main_model,effort,requests,
                output_tokens,duration_s,updated FROM experience_runs WHERE owner=? AND outcome='unrated'
                ORDER BY updated DESC LIMIT ?''', (self.identity, min(max(int(limit), 1), 50)))]

    def stats(self, task_type: str | None = None, min_runs: int = 1) -> dict:
        """Per task type/model/effort over human-rated tasks. Token kinds stay separate because
        their cost differs (output, fresh input = uncached + cache writes, cache reads)."""
        q = ('SELECT * FROM experience_tasks WHERE owner=?')
        args = [self.identity]
        if task_type:
            q += ' AND task_type=?'; args.append(task_type.lower())
        groups = {}
        with self._conn() as c:
            for r in c.execute(q, args):
                g = groups.setdefault((r['task_type'], r['main_model'], r['effort'] or '-'),
                                      {'runs': 0, 'success': 0, 'task_level': 0, 'out': [], 'fresh': [],
                                       'cached': [], 'rework': []})
                g['runs'] += 1; g['task_level'] += r['granularity'] == 'task'
                if r['rework_minutes'] is not None: g['rework'].append(r['rework_minutes'])
                if r['outcome'] == 'success':
                    g['success'] += 1
                    g['out'].append(r['output_tokens'] or 0)
                    g['fresh'].append((r['input_tokens'] or 0) + (r['cache_write_tokens'] or 0))
                    g['cached'].append(r['cache_read_tokens'] or 0)
        rows = []
        for (tt, model, effort), g in sorted(groups.items(), key=lambda x: (x[0][0] or '', x[0][1] or '')):
            if g['runs'] < min_runs:
                continue
            med = lambda v: int(statistics.median(v)) if v else None  # noqa: E731
            rows.append({'task_type': tt, 'model': model, 'effort': effort, 'runs': g['runs'],
                         'task_level_runs': g['task_level'],
                         'success_rate': round(g['success'] / g['runs'], 3),
                         'median_out_per_success': med(g['out']), 'median_fresh_per_success': med(g['fresh']),
                         'median_cached_per_success': med(g['cached']),
                         'median_rework_minutes': med(g['rework']),
                         'sufficient': g['task_level'] >= SUFFICIENT_RUNS})
        return {'groups': rows, 'api_cost_usd': None, 'pro_quota': None,
                'note': ('Human-rated only. API cost and Pro quota are not observable from transcripts and are '
                         f'never estimated. sufficient=true needs >= {SUFFICIENT_RUNS} task-level ratings; '
                         'even then it is a hint, not a quality comparison.')}

    def export(self, out: Path, min_runs: int = 3) -> dict:
        data = {'generated': int(time.time()), 'owner': self.identity, 'min_runs': min_runs,
                'groups': self.stats(min_runs=min_runs)['groups'],
                'usage': ('Advisory input for the existing MA Auto Router. Do not switch models automatically: '
                          'only groups with sufficient=true may be proposed, and a change needs a fixed-quality '
                          'A/B comparison and human approval.')}
        out = Path(out).expanduser()
        tmp = out.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
        os.replace(tmp, out)
        return {'written': str(out), 'groups': len(data['groups'])}


def from_config(path: Path) -> Experience:
    conf = json.loads(Path(path).expanduser().resolve(strict=True).read_text(encoding='utf-8'))
    db = Path(conf['state_db']).expanduser()
    if not db.is_absolute():
        db = (Path(path).resolve().parent / db).resolve()
    projects = set(conf['allowed_projects'])
    return Experience(db, conf['identity'], projects, conf.get('default_project', sorted(projects)[0]),
                      conf.get('projects_by_path'), conf.get('transcript_root'))


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--config', type=Path, required=True)
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('hook')
    r = sub.add_parser('rate'); r.add_argument('session'); r.add_argument('outcome', choices=OUTCOMES)
    r.add_argument('--task-type', required=True); r.add_argument('--note', default='')
    r.add_argument('--turns', help='only user turns A-B of the session, e.g. 3-7')
    r.add_argument('--rework-minutes', type=int)
    sub.add_parser('unrated')
    s = sub.add_parser('stats'); s.add_argument('--task-type')
    e = sub.add_parser('export'); e.add_argument('--out', type=Path, required=True)
    e.add_argument('--min-runs', type=int, default=3)
    a = p.parse_args()
    if a.cmd == 'hook':
        # A Stop hook must never block or slow Claude down: swallow every error.
        try:
            raw = sys.stdin.read(1_000_000)
            from_config(a.config).record(json.loads(raw))
        except Exception as exc:  # noqa: BLE001
            try:
                log = Path(a.config).expanduser().resolve().parent / 'experience-hook.log'
                with open(log, 'a', encoding='utf-8') as fh:
                    fh.write(f'{int(time.time())} {type(exc).__name__}: {str(exc)[:200]}\n')
            except OSError:
                pass
        return 0
    try:
        x = from_config(a.config)
        if a.cmd == 'rate':
            tr = tuple(int(v) for v in a.turns.split('-', 1)) if a.turns else None
            if tr and len(tr) == 1: tr = (tr[0], tr[0])
            out = x.rate(a.session, a.outcome, a.task_type, a.note, tr, a.rework_minutes)
        elif a.cmd == 'unrated': out = {'sessions': x.unrated()}
        elif a.cmd == 'stats': out = x.stats(a.task_type)
        else: out = x.export(a.out, a.min_runs)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    except (OSError, ValueError, KeyError, PermissionError) as exc:
        print(f'ERROR: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
