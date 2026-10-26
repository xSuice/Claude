"""Shared helpers for the V16 benchmark checks.

A check never trusts the solution: it copies the result folder, runs the solution's own commands in the JARVIS sandbox
(bwrap on the server, winsandbox on Windows) with a timeout, feeds it a HIDDEN input made by the task's generator with a
seed the solution never saw, and compares with values the check computes itself.
Result: JSON on stdout  {"task", "criteria": [{"id", "ok", "detail"}], "passed", "total", "complete"}.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNTIME_CANDIDATES = [Path.home() / '.local/share/ma-jarvis/current/brain-runtime',
                      HERE.parent / 'core' / 'brain-runtime']
HIDE = [str(Path.home() / p) for p in ('.ssh', '.claude', '.config', 'MA-Server', 'jarvis-stage', 'jarvis-loadtest',
                                        '.local/share/ma-jarvis')] + ['/srv/ma-home/library']


class Check:
    def __init__(self, task: str, result_dir: str):
        self.task = task
        self.src = Path(result_dir).resolve()
        self.tmp = Path(tempfile.mkdtemp(prefix=f'bench-{task}-'))
        self.work = self.tmp / 'work'
        if self.src.is_dir():
            shutil.copytree(self.src, self.work, symlinks=False, ignore_dangling_symlinks=True,
                            ignore=shutil.ignore_patterns('.git', '__pycache__', '.jarvis*'))
        else:
            self.work.mkdir()
        self.criteria = []

    def ok(self, cid: str, cond: bool, detail: str = '') -> bool:
        self.criteria.append({'id': cid, 'ok': bool(cond), 'detail': str(detail)[:400]})
        return bool(cond)

    def file(self, rel: str) -> Path:
        return self.work / rel

    def run(self, argv: list[str], timeout: int = 120, cwd: Path | None = None) -> tuple[int, str]:
        """Run untrusted solution code isolated: no network, only the copied work folder writable."""
        cwd = cwd or self.work
        env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': str(self.work), 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
               'MPLBACKEND': 'Agg', 'TZ': 'Europe/Berlin'}
        if os.name == 'nt':
            sys.path.insert(0, str(HERE.parent.parent.parent / 'scripts' / 'jarvis'))
            import winsandbox as w
            r = w.Sandbox().run(argv, cwd, w.Limits(timeout_s=timeout, mem_mb=2048))
            return r.code, r.output
        sandbox = None
        for c in RUNTIME_CANDIDATES:
            if (c / 'sandbox.py').is_file():
                sys.path.insert(0, str(c))
                import sandbox  # noqa: F811
                break
        if sandbox is None or not sandbox.available():
            return 125, 'keine Sandbox verfügbar - Prüfung verweigert (fail closed)'
        wrapped = sandbox.wrap(argv, self.work, cwd, env, HIDE)
        try:
            p = subprocess.run(wrapped, capture_output=True, text=True, errors='replace', timeout=timeout, env=env)
            return p.returncode, (p.stdout + p.stderr)[-6000:]
        except subprocess.TimeoutExpired:
            return 124, 'timeout'

    def done(self) -> dict:
        passed = sum(c['ok'] for c in self.criteria)
        res = {'task': self.task, 'criteria': self.criteria, 'passed': passed, 'total': len(self.criteria),
               'complete': bool(self.criteria) and passed == len(self.criteria)}
        shutil.rmtree(self.tmp, ignore_errors=True)
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return res


def guard(c: Check, cid: str, fn):
    """Run one criterion; any exception counts as a failed criterion, never as a crash of the check."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return c.ok(cid, False, f'{type(e).__name__}: {e}')
