#!/usr/bin/env python3
"""V9 controlled self-improvement: test a proposed patch in isolation, keep it only if proven.

trial    Applies a patch in a detached git worktree, runs the same allowlisted checks on the
         unchanged baseline and on the candidate, and records both in an impact register.
         Verdict: improved (a check fails before and passes after, nothing regresses),
         neutral (all pass in both), rejected (anything fails in the candidate).
         Patches touching protected paths (acceptance tests, evals, configs) are refused,
         so a candidate can never weaken the criteria it is judged by.
promote  Only with `allow_promote` in the config, an unchanged HEAD and a clean tree:
         applies the patch as one commit, re-runs the checks on the real repo and reverts
         automatically if they fail. Neutral trials need `allow_neutral`.
rollback Reverts a promoted trial with `git revert` (history is kept).
No Claude calls: patches come from a Claude session, a human or an earlier proposal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from brain_core import Brain  # noqa: E402
import runner  # noqa: E402
import sandbox  # noqa: E402
import unicodedata  # noqa: E402

MAX_PATCH = 200_000
DEFAULT_PROTECTED = [
    # acceptance criteria
    'tests/', 'test/', 'brain-runtime/tests/', 'brain-runtime/evals/', 'evals/', '.github/', 'MANIFEST-SHA256.txt',
    # security boundaries: Claude Code permissions/hook wiring and the brain's own guard code
    '.claude/settings.json', '.claude/settings.local.json', 'brain-runtime/sandbox.py', 'brain-runtime/runner.py',
    'brain-runtime/improve.py', 'brain-runtime/autonomy.py', 'brain-runtime/executive.py']
SCHEMA = '''CREATE TABLE IF NOT EXISTS improvement_journal(
    id INTEGER PRIMARY KEY AUTOINCREMENT, trial INTEGER NOT NULL, step TEXT NOT NULL, detail TEXT, at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS improvement_trials(
    id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL, project TEXT NOT NULL,
    repo TEXT NOT NULL, base_commit TEXT NOT NULL, patch_sha256 TEXT NOT NULL, patch TEXT NOT NULL,
    files TEXT NOT NULL, description TEXT NOT NULL, results TEXT NOT NULL,
    verdict TEXT NOT NULL CHECK(verdict IN ('improved','neutral','rejected','invalid')),
    created INTEGER NOT NULL, promoted_commit TEXT, status TEXT NOT NULL DEFAULT 'recorded'
        CHECK(status IN ('recorded','promoted','reverted','rolled_back')))'''


def git(repo: Path, *args, check=True, input_text=None) -> str:
    env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'LC_ALL': 'C', 'HOME': str(repo),
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_TERMINAL_PROMPT': '0'}
    p = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', *args],
                       cwd=repo, capture_output=True, text=True, input=input_text, env=env, timeout=120)
    if check and p.returncode != 0:
        raise RuntimeError(f'git {args[0]} failed: {runner.redact(p.stderr.strip())[:300]}')
    return p.stdout


def _unquote(p: str) -> str:
    if len(p) >= 2 and p[0] == '"' and p[-1] == '"':
        import codecs
        return codecs.escape_decode(p[1:-1].encode())[0].decode('utf-8', 'replace')
    return p


def _header_paths(patch: str) -> list[str]:
    """Every path named in git patch headers (both sides), including quoted names."""
    out = []
    for line in patch.splitlines():
        for key in ('rename from ', 'rename to ', 'copy from ', 'copy to '):
            if line.startswith(key):
                out.append(_unquote(line[len(key):]))
        if line.startswith(('--- ', '+++ ')):
            name = _unquote(line[4:].split('\t')[0])
            if name != '/dev/null':
                out.append(name[2:] if name[:2] in ('a/', 'b/') else name)
    return out


def threading_main() -> bool:
    import threading
    return threading.current_thread() is threading.main_thread()


def _raise_exit(signum, frame):
    raise SystemExit(128 + signum)


class Improver:
    def __init__(self, brain: Brain, actions_cfg: dict, repo: Path, *, allow_promote=False,
                 allow_neutral=False, protected: list[str] | None = None, max_trials_per_day=3,
                 sandbox: bool = True, require_sandbox: bool = True, sandbox_hide: list[str] | None = None):
        self.brain = brain
        self.actions = runner.validate(actions_cfg)['actions']
        self.repo = Path(repo).expanduser().resolve(strict=True)
        if git(self.repo, 'rev-parse', '--show-toplevel').strip() != str(self.repo):
            raise ValueError('repo must be the top level of a git repository')
        self.allow_promote, self.allow_neutral = allow_promote, allow_neutral
        self.protected = protected if protected is not None else DEFAULT_PROTECTED
        if type(max_trials_per_day) is not int or not 1 <= max_trials_per_day <= 20:
            raise ValueError('max_trials_per_day 1..20')
        self.max_trials = max_trials_per_day
        # V9.1: candidate code runs jailed; without a working jail no trial runs (fail closed).
        self.use_sandbox, self.require_sandbox = sandbox, require_sandbox
        self.hide = [str(self.repo), str(brain.db_path.parent), *(sandbox_hide or [])]
        with brain.connection(True) as db:
            db.executescript(SCHEMA)

    def _clean(self) -> bool:
        return git(self.repo, 'status', '--porcelain', '--untracked-files=no').strip() == ''

    def _files(self, patch: str) -> tuple[list[str], str | None]:
        """All paths a patch touches - old AND new side of renames/copies/deletes - plus a
        reason if it uses something we never accept (symlinks, submodules, binary data)."""
        raw = git(self.repo, 'apply', '--numstat', '-z', '-', input_text=patch)
        parts, files, binary = raw.split('\0'), [], False
        i = 0
        while i < len(parts):
            head = parts[i]
            if not head:
                i += 1; continue
            cols = head.split('\t')
            if len(cols) < 3:
                i += 1; continue
            binary |= cols[0] == '-' or cols[1] == '-'
            if cols[2]:                      # plain entry: path is in the same field
                files.append(cols[2]); i += 1
            else:                            # rename/copy: old and new path follow
                files += [parts[i + 1], parts[i + 2]]; i += 3
        files += _header_paths(patch)  # numstat omits the old side of renames/copies
        summary = git(self.repo, 'apply', '--summary', '-', input_text=patch)
        reason = None
        if binary or 'GIT binary patch' in patch:
            reason = 'binary changes are not accepted'
        elif any(m in summary for m in (' 120000', ' 160000')) or '\nnew file mode 120000' in patch \
                or 'mode 160000' in patch or '\nnew mode 120000' in patch:
            reason = 'symlinks and submodules are not accepted'
        return list(dict.fromkeys(files)), reason

    def _protected_hit(self, f: str) -> bool:
        norm = unicodedata.normalize('NFC', f.replace('\\', '/')).casefold()
        while norm.startswith('./'):
            norm = norm[2:]
        if norm.startswith('/') or norm.startswith('../') or '/../' in norm or norm.startswith('.git/'):
            return True
        return any(norm == p.rstrip('/').casefold() or norm.startswith(p.casefold()) for p in self.protected)

    def trial(self, project: str, patch: str, checks: list[str], description: str) -> dict:
        project = self.brain._project(project)
        if not isinstance(patch, str) or not patch.strip() or len(patch) > MAX_PATCH:
            raise ValueError(f'patch must be 1..{MAX_PATCH} characters')
        if not checks or any(c not in self.actions or 'claude_template' in self.actions[c] for c in checks):
            raise ValueError('checks must be local allowlisted actions')
        if not isinstance(description, str) or not 3 <= len(description) <= 300:
            raise ValueError('description 3..300 characters')
        now = int(time.time())
        with self.brain.connection() as db:
            n = db.execute('SELECT COUNT(*) FROM improvement_trials WHERE owner=? AND created>=?',
                           (self.brain.identity, now - 86400)).fetchone()[0]
        if n >= self.max_trials:
            raise PermissionError('daily trial limit reached')
        try:
            files, reason = self._files(patch)
        except RuntimeError:
            files, reason = [], None  # not a valid patch -> recorded as invalid
        bad = [f for f in files if self._protected_hit(f)]
        jail = None
        if self.use_sandbox:
            if sandbox.available():
                jail = {'hide': self.hide}
            elif self.require_sandbox:
                reason = reason or 'sandbox unavailable: refusing to run candidate code unisolated'
        base = git(self.repo, 'rev-parse', 'HEAD').strip()
        results, verdict = {}, 'invalid'
        if reason:
            results = {'error': reason, 'paths': bad[:10]}
        elif bad or not files:
            results = {'error': 'patch touches protected or invalid paths', 'paths': bad[:10]}
        else:
            tmp = Path(tempfile.mkdtemp(prefix='brain-trial-'))
            try:
                trees = {}
                for name in ('baseline', 'candidate'):
                    trees[name] = tmp / name
                    git(self.repo, 'worktree', 'add', '--detach', str(trees[name]), base)
                try:
                    git(trees['candidate'], 'apply', '--check', '-', input_text=patch); ok = True
                except RuntimeError:
                    ok = False
                if not ok:
                    results = {'error': 'patch does not apply to HEAD'}
                else:
                    git(trees['candidate'], 'apply', '-', input_text=patch)
                    for name, tree in trees.items():
                        results[name] = {c: {k: v for k, v in runner.run(self.actions[c], tree, jail).items()
                                             if k in ('exit', 'ok', 'ms', 'output_sha256', 'sandboxed')}
                                         for c in checks}
                    b, c = results['baseline'], results['candidate']
                    if not all(c[x]['ok'] for x in checks):
                        verdict = 'rejected'
                    elif any(not b[x]['ok'] for x in checks):
                        verdict = 'improved'
                    else:
                        verdict = 'neutral'
                    results['ms_baseline'] = sum(b[x]['ms'] for x in checks)
                    results['ms_candidate'] = sum(c[x]['ms'] for x in checks)
            finally:
                for tree in (tmp / 'baseline', tmp / 'candidate'):
                    if tree.exists():
                        git(self.repo, 'worktree', 'remove', '--force', str(tree), check=False)
                git(self.repo, 'worktree', 'prune', check=False)
                shutil.rmtree(tmp, ignore_errors=True)
        sha = hashlib.sha256(patch.encode()).hexdigest()
        with self.brain.connection(True) as db:
            cur = db.execute('INSERT INTO improvement_trials(owner,project,repo,base_commit,patch_sha256,patch,files,'
                             'description,results,verdict,created) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                             (self.brain.identity, project, str(self.repo), base, sha, patch, json.dumps(files),
                              description, json.dumps(results), verdict, now))
            tid = cur.lastrowid
        return {'trial': tid, 'verdict': verdict, 'files': files, 'results': results}

    def _get(self, tid: int):
        with self.brain.connection() as db:
            r = db.execute('SELECT * FROM improvement_trials WHERE id=? AND owner=?', (tid, self.brain.identity)).fetchone()
        if not r:
            raise PermissionError('trial not found')
        return dict(r)

    def _set(self, tid, **kw):
        with self.brain.connection(True) as db:
            db.execute('UPDATE improvement_trials SET ' + ','.join(f'{k}=?' for k in kw) + ' WHERE id=?',
                       (*kw.values(), tid))

    # ---------- V10.1: transactional promotion ----------
    def _journal(self, tid, step, **detail):
        with self.brain.connection(True) as db:
            db.execute('INSERT INTO improvement_journal(trial,step,detail,at) VALUES(?,?,?,?)',
                       (tid, step, json.dumps(detail, ensure_ascii=False)[:2000], int(time.time())))

    def _restore(self, tid, pre: str, why: str):
        """Return the repository to the exact pre-promotion commit; tracked files only."""
        try:
            git(self.repo, 'reset', '-q', '--hard', pre)
            ok = git(self.repo, 'rev-parse', 'HEAD').strip() == pre and self._clean()
        except Exception as e:  # noqa: BLE001
            ok, why = False, f'{why}; restore error {type(e).__name__}'
        self._journal(tid, 'restored' if ok else 'restore_failed', reason=why, pre_head=pre)
        if not ok:
            raise RuntimeError(f'SAFE STOP: could not restore {self.repo}. Run: git -C {self.repo} reset --hard {pre}')

    def _post_checks(self, checks, jail):
        return {c: runner.run(self.actions[c], self.repo, jail)['ok'] for c in checks}

    def promote(self, tid: int) -> dict:
        """Preflight without side effects -> journal -> apply+commit -> isolated post-checks.
        Any failure, exception, timeout or signal after the first mutation restores the
        pre-promotion commit (no extra revert commits). A hard crash is repaired by recover()."""
        t = self._get(tid)
        if not self.allow_promote:
            raise PermissionError('promotion disabled (allow_promote=false)')
        if t['status'] != 'recorded' or t['verdict'] not in ('improved', 'neutral'):
            raise PermissionError(f"trial is {t['status']}/{t['verdict']}")
        if t['verdict'] == 'neutral' and not self.allow_neutral:
            raise PermissionError('neutral trials need allow_neutral')
        import fcntl
        lockf = open(Path(git(self.repo, 'rev-parse', '--git-dir').strip()
                          if Path(git(self.repo, 'rev-parse', '--git-dir').strip()).is_absolute()
                          else self.repo / '.git') / 'brain-promote.lock', 'w')
        fcntl.flock(lockf, fcntl.LOCK_EX)  # serialises promotions; HEAD is re-checked under the lock
        old_handler = None
        try:
            # ---- preflight: nothing is changed before all of this holds ----
            pre = git(self.repo, 'rev-parse', 'HEAD').strip()
            if pre != t['base_commit'] or not self._clean():
                raise PermissionError('repository changed since the trial - run a new trial')
            jail = None
            if self.use_sandbox:
                if sandbox.available():
                    jail = {'hide': self.hide}
                elif self.require_sandbox:
                    raise PermissionError('sandbox unavailable: promotion refused before any change')
            checks = list(json.loads(t['results'])['candidate'])
            if any(c not in self.actions for c in checks):
                raise PermissionError('a check of this trial is no longer allowlisted')
            git(self.repo, 'apply', '--check', '--index', '-', input_text=t['patch'])
            self._journal(tid, 'preflight_ok', pre_head=pre)
            if threading_main():
                import signal
                old_handler = signal.signal(signal.SIGTERM, _raise_exit)
            try:
                git(self.repo, 'apply', '--index', '-', input_text=t['patch'])
                self._journal(tid, 'applied')
                git(self.repo, '-c', 'user.name=MA-Home Brain', '-c', 'user.email=brain@localhost', 'commit',
                    '-q', '-m', f"brain trial #{tid}: {t['description']}\n\nVerdict: {t['verdict']}; patch {t['patch_sha256'][:12]}")
                commit = git(self.repo, 'rev-parse', 'HEAD').strip()
                self._journal(tid, 'committed', commit=commit)
                post = self._post_checks(checks, jail)
            except BaseException as e:
                self._restore(tid, pre, f'{type(e).__name__} after mutation')
                raise
            if not all(post.values()):
                self._restore(tid, pre, f'post-checks failed: {post}')
                self._set(tid, status='reverted', promoted_commit=commit)
                return {'trial': tid, 'status': 'reverted', 'post_checks': post}
            self._journal(tid, 'promoted', commit=commit)
            self._set(tid, status='promoted', promoted_commit=commit)
            return {'trial': tid, 'status': 'promoted', 'commit': commit, 'post_checks': post}
        finally:
            if old_handler is not None:
                import signal
                signal.signal(signal.SIGTERM, old_handler)
            fcntl.flock(lockf, fcntl.LOCK_UN); lockf.close()

    def recover(self) -> dict:
        """After a hard crash (kill -9, power loss) mid-promotion: restore the journaled pre-HEAD
        if the repository still shows that promotion's commit or uncommitted patch state."""
        restored, untouched = [], []
        with self.brain.connection() as db:
            rows = db.execute('SELECT trial, step, detail FROM improvement_journal WHERE id IN '
                              '(SELECT MAX(id) FROM improvement_journal GROUP BY trial)').fetchall()
            pre_by = {r[0]: json.loads(r[1]).get('pre_head') for r in db.execute(
                "SELECT trial, detail FROM improvement_journal WHERE step='preflight_ok'")}
        head = git(self.repo, 'rev-parse', 'HEAD').strip()
        msg = git(self.repo, 'log', '-1', '--format=%s').strip()
        for tid, step, _ in rows:
            if step not in ('preflight_ok', 'applied', 'committed') or not pre_by.get(tid):
                continue
            pre = pre_by[tid]
            ours = msg.startswith(f'brain trial #{tid}:') and git(self.repo, 'rev-parse', 'HEAD^').strip() == pre
            if ours or (head == pre and not self._clean()):
                self._restore(tid, pre, 'recover after crash'); restored.append(tid)
            else:
                self._journal(tid, 'recover_skipped', head=head); untouched.append(tid)
        return {'restored': restored, 'left_alone': untouched}

    def rollback(self, tid: int) -> dict:
        t = self._get(tid)
        if t['status'] != 'promoted':
            raise PermissionError('only promoted trials can be rolled back')
        if not self._clean():
            raise PermissionError('working tree not clean')
        git(self.repo, '-c', 'user.name=MA-Home Brain', '-c', 'user.email=brain@localhost',
            'revert', '--no-edit', t['promoted_commit'])
        self._set(tid, status='rolled_back')
        return {'trial': tid, 'status': 'rolled_back', 'revert_of': t['promoted_commit']}

    def register(self, limit=20) -> list[dict]:
        """Impact register: what was tried, how it was judged, what is live."""
        with self.brain.connection() as db:
            rows = db.execute('SELECT id,project,description,verdict,status,files,results,created,promoted_commit '
                              'FROM improvement_trials WHERE owner=? ORDER BY id DESC LIMIT ?',
                              (self.brain.identity, min(max(int(limit), 1), 100))).fetchall()
        return [{**dict(r), 'files': json.loads(r['files']), 'results': json.loads(r['results'])} for r in rows]


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--config', type=Path, required=True, help='brain config; optional key "improve": '
                   '{"allow_promote": false, "allow_neutral": false, "protected": [...], "max_trials_per_day": 3}')
    p.add_argument('--actions', type=Path, required=True)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--project', required=True)
    sub = p.add_subparsers(dest='cmd', required=True)
    t = sub.add_parser('trial'); t.add_argument('patch', type=Path); t.add_argument('--check', action='append', required=True)
    t.add_argument('--description', required=True)
    for name in ('promote', 'rollback'):
        sub.add_parser(name).add_argument('trial', type=int)
    sub.add_parser('recover')
    sub.add_parser('register')
    a = p.parse_args()
    try:
        conf = json.loads(a.config.resolve(strict=True).read_text(encoding='utf-8'))
        db = Path(conf['state_db']).expanduser()
        if not db.is_absolute(): db = (a.config.resolve().parent / db).resolve()
        opts = conf.get('improve', {})
        imp = Improver(Brain(db, conf['identity'], set(conf['allowed_projects'])), runner.load_actions(a.actions),
                       a.repo, allow_promote=bool(opts.get('allow_promote')), allow_neutral=bool(opts.get('allow_neutral')),
                       protected=opts.get('protected'), max_trials_per_day=opts.get('max_trials_per_day', 3))
        if a.cmd == 'trial':
            out = imp.trial(a.project, a.patch.read_text(encoding='utf-8'), a.check, a.description)
        elif a.cmd == 'promote': out = imp.promote(a.trial)
        elif a.cmd == 'rollback': out = imp.rollback(a.trial)
        elif a.cmd == 'recover': out = imp.recover()
        else: out = imp.register()
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    except (OSError, ValueError, KeyError, PermissionError, RuntimeError) as e:
        print(f'ERROR: {type(e).__name__}: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
