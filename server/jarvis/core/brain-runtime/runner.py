"""V9 bounded execution of admin-allowlisted actions. No shell, no placeholders, no LLM.

actions.json (admin-owned, not group/world writable):
{"actions": {
   "tests":  {"argv": ["python3", "-m", "unittest", "discover", "-s", "tests", "-q"],
              "cwd": ".", "timeout": 600, "mem_mb": 2048, "idempotent": true},
   "lint":   {"argv": ["python3", "-m", "compileall", "-q", "."], "cwd": ".", "timeout": 120},
   "audit":  {"claude_template": "repo_audit"}},
 "limits": {"max_steps_per_run": 3, "max_local_runs_per_day": 60, "max_attempts": 2}}

Relative `cwd` is resolved against the caller's base directory (the project workspace for
the executive, the isolated worktree for improvement trials) and must stay inside it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

import secretscan

NAME = re.compile(r'^[a-z][a-z0-9_-]{0,39}$')
ACTION_KEYS = {'argv', 'cwd', 'timeout', 'mem_mb', 'idempotent', 'claude_template', 'env', 'auto', 'sandbox', 'risk',
               'helper_task', 'fallback_template', 'verify'}
LIMIT_KEYS = {'max_steps_per_run': (1, 20, 3), 'max_local_runs_per_day': (1, 1000, 60),
              'max_attempts': (1, 5, 2)}
TAIL = 800


def redact(text: str) -> str:
    """One rule set for input gate, logs, events and prompts: see secretscan.py."""
    return secretscan.redact(text)


def load_actions(path: Path) -> dict:
    path = Path(path).expanduser().resolve(strict=True)
    if os.name == 'posix' and path.stat().st_mode & 0o022:
        raise PermissionError('actions config must not be group/world writable')
    return validate(json.loads(path.read_text(encoding='utf-8')))


def validate(cfg: dict) -> dict:
    if not isinstance(cfg, dict) or set(cfg) - {'actions', 'limits'} or not isinstance(cfg.get('actions'), dict):
        raise ValueError('actions config needs {"actions": {...}, "limits": {...}}')
    for name, a in cfg['actions'].items():
        if not NAME.match(name) or not isinstance(a, dict) or set(a) - ACTION_KEYS:
            raise ValueError(f'invalid action {name!r}')
        for flag in ('auto', 'idempotent', 'sandbox'):
            if flag in a and type(a[flag]) is not bool:
                raise ValueError(f'{name}: {flag} must be true/false')
        if a.get('risk', 'reversible') not in ('read', 'reversible', 'privileged'):
            raise ValueError(f'{name}: risk must be read, reversible or privileged')
        if a.get('risk') == 'privileged' and a.get('auto'):
            raise ValueError(f'{name}: privileged actions can never be auto')
        if 'helper_task' in a:  # V11: cloud helper via provider_adapter, optional Claude fallback
            if set(a) - {'helper_task', 'fallback_template', 'auto', 'risk', 'verify'} or not NAME.match(str(a['helper_task'])):
                raise ValueError(f'{name}: helper actions take helper_task (+ fallback_template, verify)')
            v = a.get('verify')
            if v is not None and (not isinstance(v, dict) or v.get('type') not in ('grounded', 'contains', 'json_keys')):
                raise ValueError(f'{name}: verify.type must be grounded, contains or json_keys')
            if a.get('risk') == 'privileged':
                raise ValueError(f'{name}: helper actions cannot be privileged')
            continue
        if 'claude_template' in a:
            if set(a) - {'claude_template', 'auto', 'risk'} or not NAME.match(str(a['claude_template'])):
                raise ValueError(f'{name}: claude actions take only claude_template')
            continue
        argv = a.get('argv')
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
            raise ValueError(f'{name}: argv must be a non-empty list of strings')
        if Path(argv[0]).name in ('sh', 'bash', 'zsh', 'dash', 'cmd', 'cmd.exe', 'powershell', 'pwsh', 'sudo', 'su'):
            raise ValueError(f'{name}: shells and privilege tools are not allowed as actions')
        t = a.get('timeout', 300)
        if type(t) is not int or not 1 <= t <= 3600:
            raise ValueError(f'{name}: timeout 1..3600')
        m = a.get('mem_mb', 2048)
        if type(m) is not int or not 64 <= m <= 32768:
            raise ValueError(f'{name}: mem_mb 64..32768')
        if 'env' in a and not (isinstance(a['env'], dict) and all(
                re.match(r'^[A-Z][A-Z0-9_]{0,40}$', k) and isinstance(v, str) for k, v in a['env'].items())):
            raise ValueError(f'{name}: env must map UPPER_CASE names to strings')
    limits = cfg.get('limits', {})
    if not isinstance(limits, dict) or set(limits) - set(LIMIT_KEYS):
        raise ValueError('unknown limits')
    for k, (lo, hi, default) in LIMIT_KEYS.items():
        v = limits.get(k, default)
        if type(v) is not int or not lo <= v <= hi:
            raise ValueError(f'limit {k} must be {lo}..{hi}')
        limits[k] = v
    cfg['limits'] = limits
    return cfg


def _limits(mem_mb: int, cpu_s: int):
    def apply():
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (mem_mb * 1024 * 1024,) * 2)
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s + 5))
            os.setsid()
        except (ImportError, ValueError, OSError):
            pass
    return apply if os.name == 'posix' else None


def run(action: dict, base: Path, sandbox: dict | None = None) -> dict:
    """Run one local action. Returns exit code, duration and a short redacted output tail.
    sandbox={'hide': [...]} runs it in sandbox.py's jail (only `base` writable, no network)."""
    if 'claude_template' in action:
        raise ValueError('claude actions go through the bounded autonomy queue')
    base = Path(base).resolve(strict=True)
    cwd = (base / action.get('cwd', '.')).resolve()
    if cwd != base and base not in cwd.parents:
        raise PermissionError('action cwd escapes the workspace')
    timeout, mem = action.get('timeout', 300), action.get('mem_mb', 2048)
    env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'LC_ALL': 'C.UTF-8', 'HOME': str(base),
           'PYTHONDONTWRITEBYTECODE': '1', **action.get('env', {})}
    argv = action['argv']
    if sandbox is not None:
        import sandbox as jail
        argv = jail.wrap(argv, base, cwd, env, list(sandbox.get('hide', [])))
    start = time.monotonic()
    try:
        p = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, errors='replace', env=env,
                             preexec_fn=_limits(mem, timeout))
        try:
            out, _ = p.communicate(timeout=timeout)
            code = p.returncode
        except subprocess.TimeoutExpired:
            try:
                os.killpg(p.pid, 9) if os.name == 'posix' else p.kill()  # whole process group
            except OSError:
                p.kill()
            out, _ = p.communicate()
            code, out = 124, (out or '') + '\n[timeout]'
    except FileNotFoundError:
        code, out = 127, 'program not found'
    out = out or ''
    return {'exit': code, 'ok': code == 0, 'ms': int((time.monotonic() - start) * 1000),
            'output_sha256': hashlib.sha256(out.encode('utf-8', 'replace')).hexdigest()[:16],
            'tail': redact(out[-TAIL:]), 'sandboxed': sandbox is not None}
