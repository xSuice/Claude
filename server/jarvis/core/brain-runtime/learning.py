"""V16 learning that can be checked: only from results the deterministic acceptance confirmed.

Procedural memory ("skill compiler"): a plan whose job ended `done` (every result file passed the
independent acceptance) becomes a template, keyed by task type, keywords and the normalised request.
  * exact repeat (same normalised request)  -> the plan is reused unchanged: no planning call at all
  * same type, other details (keyword similarity >= threshold) -> the plan is given to the planner as a
    worked example and adapted by a smaller model; request-specific checks stay request-specific,
    so quality checks are never weakened by reuse
Templates that fail repeatedly are retired automatically; `retract()` removes one immediately.
Lessons (episodic -> semantic): when a job needed correction rounds and still ended `done`, the
first failure is stored as a short lesson for that task type and shown to the planner next time.
Metacognition: per task type success rate and cost, used to state uncertainty honestly.
Consolidation is event/idle driven, local and model-free (dedupe, expiry, pruning).
Nothing here edits code, spends tokens or changes permissions.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
from pathlib import Path

from brain_core import keywords

SCHEMA = '''
CREATE TABLE IF NOT EXISTS plan_templates(
    id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL, project TEXT NOT NULL, task_type TEXT NOT NULL,
    request_hash TEXT NOT NULL, keywords TEXT NOT NULL, plan TEXT NOT NULL, data_class TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active','retired','retracted')), source_job TEXT NOT NULL,
    uses INTEGER NOT NULL DEFAULT 0, successes INTEGER NOT NULL DEFAULT 1, failures INTEGER NOT NULL DEFAULT 0,
    best_list_usd REAL, best_tokens INTEGER, created INTEGER NOT NULL, updated INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS plan_templates_scope ON plan_templates(owner, project, status);
CREATE TABLE IF NOT EXISTS lessons(
    id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL, project TEXT NOT NULL, task_type TEXT NOT NULL,
    text TEXT NOT NULL, source_job TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','retracted')),
    created INTEGER NOT NULL, UNIQUE(owner, project, task_type, text));
'''
RANK = {'public': 0, 'internal': 1, 'private': 2}
STOP = {'und', 'oder', 'der', 'die', 'das', 'ein', 'eine', 'einen', 'mit', 'für', 'mir', 'bitte', 'aus', 'in', 'im', 'zu', 'von',
        'the', 'and', 'for', 'with', 'of', 'to', 'erstelle', 'mach', 'mache', 'auf', 'als', 'den', 'dem', 'des', 'ist', 'sind'}


def norm_request(text: str) -> str:
    return re.sub(r'\s+', ' ', text.casefold()).strip()


_FOLD = str.maketrans({'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss'})
FILLER = {'bau', 'baue', 'schreib', 'schreibe', 'dazu', 'kurz', 'kurze', 'ganze', 'fuer', 'gib', 'mach', 'machen', 'brauche', 'moechte'}
_SUFFIX = ('en', 'er', 'es', 'e', 'n', 's')


def _stem(w: str) -> str:
    """Symmetric light stemmer (umlauts folded, one inflection suffix cut) so that 'römische'/'roemisch', 'Zahlen'/'Zahl',
    'Tests'/'Test' meet. It is applied to both sides at match time; stored templates stay untouched."""
    w = w.casefold().translate(_FOLD)
    for suf in _SUFFIX:
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


def kw(text: str) -> set[str]:
    """Raw keywords as stored in templates (unchanged format)."""
    return {w for w in keywords(text) if w not in STOP and len(w) > 2}


def norm_kw(words) -> set[str]:
    """Normalised comparison set from raw keywords/phrases."""
    out = set()
    for phrase in words:
        for w in keywords(phrase):
            w = w.casefold().translate(_FOLD)
            if len(w) > 2 and w not in STOP and w not in FILLER:
                st = _stem(w)
                if st not in FILLER:
                    out.add(st)
    return out


def numbers(text: str) -> set[str]:
    return set(re.findall(r'\d+', text))


class Learning:
    def __init__(self, brain, project: str, *, threshold: float = 0.35, clock=time.time):
        self.brain, self.project, self.threshold, self.clock = brain, project, threshold, clock
        with brain.connection(True) as c:
            c.executescript(SCHEMA)

    def _c(self, write=False):
        return self.brain.connection(write)

    # ---------- use ----------
    def match(self, request: str, spec: dict) -> dict | None:
        """Best active template usable for this job, or None. Data-class rule: a template learned from
        more sensitive data is never reused for a less sensitive job."""
        h = hashlib.sha256(norm_request(request).encode()).hexdigest()
        words = norm_kw(kw(request))
        rank = RANK.get(spec.get('data_class'), 1)
        with self._c() as c:
            rows = [dict(r) for r in c.execute("SELECT * FROM plan_templates WHERE owner=? AND project=? AND status='active'",
                                               (self.brain.identity, self.project))]
        best = None
        for r in rows:
            if RANK.get(r['data_class'], 2) > rank:
                continue
            if r['request_hash'] == h:
                best = {**r, 'match': 'exact', 'score': 1.0}
                break
            tk = norm_kw(json.loads(r['keywords']))
            if not words or not tk:
                continue
            score = len(words & tk) / len(words | tk)
            if score >= self.threshold and (best is None or score > best['score']):
                best = {**r, 'match': 'similar', 'score': score}
        if best:
            best['plan'] = json.loads(best['plan'])
            with self._c(True) as c:
                c.execute('UPDATE plan_templates SET uses=uses+1, updated=? WHERE id=?', (int(self.clock()), best['id']))
        return best

    def lessons(self, spec: dict, task_type: str | None = None, limit: int = 6) -> str:
        with self._c() as c:
            q = ("SELECT task_type, text FROM lessons WHERE owner=? AND project=? AND status='active' "
                 + ('AND task_type=? ' if task_type else '') + 'ORDER BY created DESC LIMIT ?')
            rows = c.execute(q, (self.brain.identity, self.project, *([task_type] if task_type else []), limit)).fetchall()
            stats = c.execute("SELECT task_type, SUM(verdict='done') ok, COUNT(*) n FROM jobs WHERE owner=? AND verdict IS NOT NULL "
                              'GROUP BY task_type ORDER BY n DESC LIMIT 8', (self.brain.identity,)).fetchall()
        parts = [f'- [{r["task_type"]}] {r["text"]}' for r in rows]
        if stats:
            parts.append('- Bisherige Erfolgsquote je Typ: ' + ', '.join(f'{s["task_type"]} {s["ok"]}/{s["n"]}' for s in stats if s['task_type']))
        return '\n'.join(parts)

    # ---------- learn ----------
    def record(self, job: dict, plan: dict, verdict: str, acceptance: dict) -> dict:
        now = int(self.clock())
        src = job.get('plan_source') or ''
        if src.startswith('local:'):
            return {}  # a locally computed answer (e.g. costs) goes stale; it is never a reusable template
        with self._c() as c:  # an unanswered question is no confirmed success (A14): never learn from it
            if any(not ((json.loads(r[0] or '{}')).get('answer') or '').strip() for r in c.execute(
                    "SELECT result FROM job_steps WHERE job_id=? AND kind='human' AND state='done'", (job.get('id'),))):
                return {}
        tid = int(src.split(':')[1]) if src.startswith('template:') else None
        ex = int(src.split(':')[2]) if src.startswith('claude:adapted:') else None
        out = {}
        with self._c(True) as c:
            for t in (tid, ex):
                if t is None:
                    continue
                if verdict == 'done':
                    c.execute('UPDATE plan_templates SET successes=successes+1, updated=? WHERE id=?', (now, t))
                else:
                    c.execute('UPDATE plan_templates SET failures=failures+1, updated=? WHERE id=?', (now, t))
                    c.execute("UPDATE plan_templates SET status='retired' WHERE id=? AND failures>=2 AND failures>successes", (t,))
            if verdict == 'done' and acceptance.get('ok') and tid is None:
                h = hashlib.sha256(norm_request(job['request']).encode()).hexdigest()
                words = sorted(kw(job['request']) | {w.casefold() for w in plan.get('match_keywords', [])})[:40]
                c.execute('INSERT INTO plan_templates(owner,project,task_type,request_hash,keywords,plan,data_class,status,source_job,'
                          'best_list_usd,best_tokens,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                          (self.brain.identity, self.project, plan['task_type'], h, json.dumps(words),
                           json.dumps(plan, ensure_ascii=False), job['spec']['data_class'], 'active', job['id'],
                           job.get('list_usd'), job.get('tokens_new'), now, now))
                out['template'] = c.execute('SELECT last_insert_rowid()').fetchone()[0]
            if verdict == 'done' and int(job.get('fix_rounds') or 0) > 0:
                first = c.execute("SELECT text FROM job_events WHERE job_id=? AND kind IN ('step_failed','correction') ORDER BY id LIMIT 1",
                                  (job['id'],)).fetchone()
                if first:
                    text = 'Erste Fassung scheiterte an: ' + re.sub(r'\s+', ' ', first['text'])[:220] + ' (danach behoben)'
                    c.execute('INSERT OR IGNORE INTO lessons(owner,project,task_type,text,source_job,created) VALUES(?,?,?,?,?,?)',
                              (self.brain.identity, self.project, plan['task_type'], text, job['id'], now))
                    out['lesson'] = text
        return out

    def retract(self, kind: str, ident: int) -> dict:
        table = {'template': 'plan_templates', 'lesson': 'lessons'}.get(kind)
        if not table:
            raise ValueError('kind must be template or lesson')
        with self._c(True) as c:
            cur = c.execute(f"UPDATE {table} SET status='retracted' WHERE id=? AND owner=? AND project=?",
                            (ident, self.brain.identity, self.project))
            if cur.rowcount != 1:
                raise PermissionError('not found')
        return {'kind': kind, 'id': ident, 'status': 'retracted'}

    def listing(self) -> dict:
        with self._c() as c:
            t = [dict(r) for r in c.execute('SELECT id,task_type,status,uses,successes,failures,best_list_usd,best_tokens,source_job '
                                            'FROM plan_templates WHERE owner=? AND project=? ORDER BY id DESC LIMIT 50',
                                            (self.brain.identity, self.project))]
            le = [dict(r) for r in c.execute('SELECT id,task_type,status,text,source_job FROM lessons WHERE owner=? AND project=? '
                                             'ORDER BY id DESC LIMIT 50', (self.brain.identity, self.project))]
        return {'templates': t, 'lessons': le}

    def metacognition(self) -> list[dict]:
        """Per task type: jobs, success rate, mean cost - the basis for honest uncertainty."""
        with self._c() as c:
            rows = c.execute("SELECT task_type, COUNT(*) n, SUM(verdict='done') ok, SUM(verdict='partial') part, "
                             'AVG(claude_calls) calls, AVG(tokens_new) tokens, AVG(list_usd) usd, AVG(fix_rounds) fixes '
                             'FROM jobs WHERE owner=? AND verdict IS NOT NULL GROUP BY task_type ORDER BY n DESC',
                             (self.brain.identity,)).fetchall()
        return [{**dict(r), 'success_rate': round((r['ok'] or 0) / r['n'], 2) if r['n'] else None,
                 'confidence': 'niedrig' if r['n'] < 3 else ('mittel' if r['n'] < 10 else 'hoch')} for r in rows]

    # ---------- consolidation (idle, model-free) ----------
    def consolidate(self, work_root: Path, keep_work_days: int = 14, keep_events_days: int = 180) -> dict:
        now = int(self.clock())
        removed_ws = 0
        with self._c(True) as c:
            c.execute("UPDATE plan_templates SET status='retired' WHERE owner=? AND status='active' AND updated<?",
                      (self.brain.identity, now - 180 * 86400))
            old = [r[0] for r in c.execute("SELECT id FROM jobs WHERE owner=? AND state IN ('done','partial','failed','cancelled') "
                                           'AND finished<?', (self.brain.identity, now - keep_work_days * 86400))]
            n_ev = c.execute("DELETE FROM job_events WHERE ts<? AND job_id IN (SELECT id FROM jobs WHERE owner=? AND "
                             "state IN ('done','partial','failed','cancelled'))", (now - keep_events_days * 86400, self.brain.identity)).rowcount
        for jid in old:
            p = Path(work_root) / jid
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)  # results stay in the results folder; only the scratch workspace goes
                removed_ws += 1
        return {'workspaces_removed': removed_ws, 'events_pruned': n_ev}
