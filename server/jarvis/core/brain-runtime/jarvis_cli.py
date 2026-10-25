#!/usr/bin/env python3
"""JARVIS V16 server CLI. Every answer is ONE JSON object on stdout (binary for *-tar commands).

  jarvis_cli.py --config CFG submit            stdin: JSON line {"request", "client_id", "options"} [+ '\n' + tar.gz of inputs]
  jarvis_cli.py --config CFG status JOB | events JOB [--since N] | list [--limit N] | result JOB | result-tar JOB
  jarvis_cli.py --config CFG cancel JOB | approve JOB [--step S] [--answer TEXT]
  jarvis_cli.py --config CFG tick [--max-seconds 50]     (cron, every minute, under flock)
  jarvis_cli.py --config CFG usage | caps [--discover] | learned | forget template|lesson ID | meta
  jarvis_cli.py --config CFG doctor | kill on|off [--global]
  jarvis_cli.py --config CFG pc-lease | pc-pull JOB | pc-push JOB STEP --ok|--fail [--detail T] | pc-report
Exit codes: 0 ok, 2 invalid input, 3 refused (permission/kill switch/secret), 1 internal error.
"""
from __future__ import annotations

import argparse
import fcntl
import io
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from brain_core import Brain  # noqa: E402
from capabilities import Registry  # noqa: E402
from ledger import Ledger, bridge_plan_probe  # noqa: E402
from learning import Learning  # noqa: E402
import sandbox  # noqa: E402
from taskengine import Engine, make_tar, safe_extract, FINAL  # noqa: E402
import stagnation  # P3: watchdog hardening
from workers import ClaudeWorker, HelperRoute  # noqa: E402

VERSION = '16.0'
DEFAULT_HIDE = ['/srv/ma-home', '/etc/ma-home', '/var/lib/postgresql', '/mnt', '/media', '/opt/ma-home', '/var/backups']


def load_config(path: str) -> dict:
    p = Path(path).expanduser().resolve(strict=True)
    if os.name == 'posix' and p.stat().st_mode & 0o022:
        raise PermissionError('config must not be group/world writable')
    cfg = json.loads(p.read_text(encoding='utf-8'))
    for k in ('identity', 'project', 'state_dir', 'results_dir', 'system_db'):
        if not cfg.get(k):
            raise ValueError(f'config needs {k}')
    return cfg


def build(cfg: dict, claude_exec=None, pressure=None, plan_probe=None) -> dict:
    state = Path(cfg['state_dir'])
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    brain = Brain(state / 'brain.db', cfg['identity'], {cfg['project']})
    probe = plan_probe if plan_probe is not None else (bridge_plan_probe(cfg['bridge_socket']) if cfg.get('bridge_socket') else None)
    ledger = Ledger(Path(cfg['system_db']), cfg.get('limits'), plan_probe=probe or None)
    hide = sorted(set(DEFAULT_HIDE + list(cfg.get('hide') or []) + [str(state), str(Path(cfg['system_db']).parent)]))
    reg = Registry(Path(cfg['system_db']), 'server', Path(cfg['tools_dir']) if cfg.get('tools_dir') else None, hide)
    claude = ClaudeWorker(cfg.get('claude_bin', str(Path.home() / '.local/bin/claude')),
                          timeout_s=int(cfg.get('claude_timeout_s', 900)), max_turns=int(cfg.get('claude_max_turns', 30)),
                          exec_fn=claude_exec)
    router = None
    if cfg.get('router_dir'):
        sys.path.insert(0, str(cfg['router_dir']))
        try:
            import router_core as router  # the one MA Auto Router (scripts/router/router_core.py)
        except ImportError:
            router = None
    route = None
    h = cfg.get('helpers') or {}
    if h.get('providers'):
        import provider_adapter
        import route_policy
        helpers = provider_adapter.HelperClient(provider_adapter.load(Path(h['providers'])), state / 'helpers.db', cfg['identity'])
        policy = route_policy.RoutePolicy(state / 'helpers.db', h.get('router_cmd'), helpers, h.get('router_mode', 'shadow'),
                                          provider_order=h.get('provider_order', ()))
        route = HelperRoute(policy, helpers, ledger, cfg['identity'], cfg['project'])
    learning = Learning(brain, cfg['project'], threshold=float(cfg.get('template_threshold', 0.35)))
    kw = {'pressure': pressure} if pressure else {}
    eng = Engine(brain=brain, project=cfg['project'], registry=reg, ledger=ledger, claude=claude, learning=learning, cfg=cfg,
                 route=route, router=router, **kw)
    return {'engine': eng, 'brain': brain, 'ledger': ledger, 'registry': reg, 'learning': learning, 'state': state}


def global_kill(cfg: dict) -> bool:
    return (Path(cfg['system_db']).parent / 'KILL').exists()


def out(obj, code=0):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, default=str) + '\n')
    sys.stdout.flush()
    return code


def read_stdin_request() -> tuple[dict, bytes]:
    raw = sys.stdin.buffer.read(260_000_000)
    head, _, rest = raw.partition(b'\n')
    req = json.loads(head.decode('utf-8') or '{}')
    if not isinstance(req, dict):
        raise ValueError('request must be a JSON object')
    return req, rest


def cmd_tick(app, cfg, a):
    if global_kill(cfg):
        return out({'idle': 'global kill switch'})
    lock = open(Path(cfg['system_db']).parent / 'tick.lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return out({'idle': 'another tick is running'})
    eng = app['engine']
    t0, c0 = time.monotonic(), time.process_time()
    res = eng.tick(max_seconds=a.max_seconds)
    with app['brain'].connection() as c:
        day = c.execute("SELECT value FROM meta WHERE k='v16-consolidated'").fetchone()
    today = time.strftime('%Y-%m-%d')
    if (not day or day[0] != today) and time.localtime().tm_hour >= int(cfg.get('consolidate_hour', 3)) and not res['worked']:
        res['consolidated'] = app['learning'].consolidate(eng.work_root)
        res['rediscovered'] = app['registry'].discover(selftest=True)
        with app['brain'].connection(True) as c:
            c.execute("INSERT OR REPLACE INTO meta(k,value) VALUES('v16-consolidated',?)", (today,))
    res['self_ms'] = int((time.monotonic() - t0) * 1000)
    res['self_cpu_ms'] = int((time.process_time() - c0) * 1000)
    if a.log and (res.get('worked') or res.get('recovered') or res.get('consolidated')):
        log = Path(a.log)
        try:
            if log.exists() and log.stat().st_size > 2_000_000:   # keep the newest half, no logrotate needed
                tail = log.read_bytes()[-1_000_000:]
                log.write_bytes(tail[tail.find(b'\n') + 1:])
            with open(log, 'a', encoding='utf-8') as fh:
                fh.write(time.strftime('%Y-%m-%dT%H:%M:%S ') + json.dumps(res, ensure_ascii=False, default=str)[:4000] + '\n')
        except OSError:
            pass
    # P3: Stagnation and loop detection (rate-limited to 3 checks)
    stagnation_conn = stagnation.get_staging_conn()
    if stagnation_conn:
        try:
            stag_results = stagnation.stagnation_check(stagnation_conn, max_checks=3)
            loop_results = stagnation.loop_detection(stagnation_conn, max_checks=3)
            res[stagnation] = stag_results
            res[loop_detection] = loop_results
        finally:
            stagnation_conn.close()
    return out(res)


def cmd_doctor(app, cfg, a):
    checks = {}
    checks['version'] = VERSION
    checks['sandbox_backend'] = sandbox.backend()
    checks['claude_cli'] = app['engine'].claude.available()
    st = app['state']
    checks['state_dir_private'] = os.name != 'posix' or not st.stat().st_mode & 0o077
    res = Path(cfg['results_dir'])
    checks['results_writable'] = os.access(res, os.W_OK) if res.exists() else False
    checks['kill_switch'] = {'identity': (st / 'KILL').exists(), 'global': global_kill(cfg)}
    du = shutil.disk_usage(st)
    checks['disk_free_gb'] = round(du.free / 1e9, 1)
    caps = app['registry'].listing()
    checks['capabilities'] = {s: sum(1 for c in caps if c['status'] == s) for s in ('tested', 'available', 'failed', 'missing', 'disabled')}
    checks['router'] = bool(app['engine'].router)
    checks['helpers'] = 'configured (mode %s)' % (cfg.get('helpers') or {}).get('router_mode', 'shadow') if (cfg.get('helpers') or {}).get('providers') else 'not configured'
    checks['ledger'] = app['ledger'].usage(cfg['identity'])
    checks['pressure'] = app['engine'].pressure()
    try:
        import subprocess
        cron = subprocess.run(['crontab', '-l'], capture_output=True, text=True, timeout=10).stdout
        checks['cron_tick'] = 'jarvis_cli.py' in cron and ' tick' in cron
    except (OSError, Exception):  # noqa: BLE001
        checks['cron_tick'] = None
    ok = checks['sandbox_backend'] is not None and checks['claude_cli'] and checks['state_dir_private'] and checks['results_writable']
    return out({'ok': bool(ok), **checks})



def approver(claimed: str | None) -> str:
    """Origin of an approval, from process metadata only. Claude workers (JARVIS_WORKER=1) can never approve. `--by portal:<user>`
    is honoured only when the portal bridge started this process (MA_JARVIS_VIA=bridge); otherwise the origin is the unix user.
    Same-uid processes can fake the environment: a separate OS account (needs sudo) is the real boundary, see the audit."""
    import getpass
    import os
    import re as _re
    if os.environ.get('JARVIS_WORKER') == '1':
        raise PermissionError('Claude-Worker dürfen nichts freigeben')
    if claimed and claimed.startswith('portal:') and os.environ.get('MA_JARVIS_VIA') == 'bridge':
        return claimed
    return 'cli:' + (_re.sub(r'[^A-Za-z0-9._-]', '', getpass.getuser())[:40] or 'unknown')


def main(argv=None):
    ap = argparse.ArgumentParser(prog='jarvis_cli.py')
    ap.add_argument('--config', required=True)
    sp = ap.add_subparsers(dest='cmd', required=True)
    sp.add_parser('submit')
    for name in ('status', 'result', 'result-tar', 'cancel', 'pc-pull'):
        sp.add_parser(name).add_argument('job')
    s = sp.add_parser('events'); s.add_argument('job'); s.add_argument('--since', type=int, default=0)
    s = sp.add_parser('list'); s.add_argument('--limit', type=int, default=20)
    s = sp.add_parser('approve'); s.add_argument('job'); s.add_argument('--step'); s.add_argument('--answer', default=''); s.add_argument('--by')
    s = sp.add_parser('tick'); s.add_argument('--max-seconds', type=int, default=50); s.add_argument('--log')
    sp.add_parser('usage'); sp.add_parser('learned'); sp.add_parser('meta'); sp.add_parser('doctor')
    s = sp.add_parser('caps'); s.add_argument('--discover', action='store_true'); s.add_argument('--no-selftest', action='store_true')
    s = sp.add_parser('forget'); s.add_argument('kind', choices=['template', 'lesson', 'memory']); s.add_argument('ident')
    s = sp.add_parser('kill'); s.add_argument('state', choices=['on', 'off']); s.add_argument('--global', dest='glob', action='store_true')
    sp.add_parser('pc-lease'); sp.add_parser('pc-report')
    s = sp.add_parser('pc-push'); s.add_argument('job'); s.add_argument('step')
    g = s.add_mutually_exclusive_group(required=True); g.add_argument('--ok', action='store_true'); g.add_argument('--fail', action='store_true')
    s.add_argument('--detail', default='')
    a = ap.parse_args(argv)
    try:
        cfg = load_config(a.config)
        app = build(cfg)
        eng = app['engine']
        if a.cmd == 'submit':
            if global_kill(cfg) or (app['state'] / 'KILL').exists():
                return out({'error': 'Not-Aus aktiv: keine neuen Aufträge'}, 3)
            req, tar = read_stdin_request()
            tmp = None
            try:
                if tar.strip():
                    tmp = Path(tempfile.mkdtemp(prefix='jarvis-in-'))
                    safe_extract(tar, tmp, max_bytes=200_000_000, max_files=500)
                r = eng.submit(str(req.get('request') or ''), client_id=req.get('client_id'), options=req.get('options') or {},
                               inputs_dir=tmp)
            finally:
                if tmp:
                    shutil.rmtree(tmp, ignore_errors=True)
            return out(r)
        if a.cmd == 'status':
            return out(eng.status(a.job))
        if a.cmd == 'events':
            return out({'job': a.job, 'events': eng.events(a.job, a.since)})
        if a.cmd == 'list':
            return out({'jobs': eng.listing(a.limit)})
        if a.cmd == 'result':
            st = eng.status(a.job)
            res = Path(st['results'])
            files = sorted(str(p.relative_to(res)).replace('\\', '/') for p in res.rglob('*') if p.is_file()) if res.exists() else []
            man = json.loads((res / 'manifest.json').read_text(encoding='utf-8')) if (res / 'manifest.json').exists() else None
            return out({'job': a.job, 'state': st['state'], 'final': st['state'] in FINAL, 'results_dir': str(res), 'files': files,
                        'manifest': man})
        if a.cmd == 'result-tar':
            st = eng.status(a.job)
            if st['state'] not in FINAL:
                return out({'error': 'job not finished'}, 2)
            sys.stdout.buffer.write(make_tar(Path(st['results'])))
            return 0
        if a.cmd == 'cancel':
            return out(eng.cancel(a.job))
        if a.cmd == 'approve':
            return out(eng.approve(a.job, a.step, a.answer, by=approver(a.by)))
        if a.cmd == 'tick':
            return cmd_tick(app, cfg, a)
        if a.cmd == 'usage':
            with app['brain'].connection() as c:
                jobs = c.execute("SELECT COUNT(*) n, SUM(verdict='done') done, SUM(claude_calls) calls, SUM(tokens_new) tok, "
                                 'SUM(tokens_cache) cache, SUM(list_usd) usd, SUM(cpu_ms) cpu FROM jobs WHERE owner=? AND created>=?',
                                 (cfg['identity'], int(time.time()) - 86400)).fetchone()
            return out({'ledger': app['ledger'].usage(cfg['identity']), 'jobs_24h': dict(jobs)})
        if a.cmd == 'caps':
            if a.discover:
                return out({'discovered': app['registry'].discover(selftest=not a.no_selftest), 'caps': app['registry'].listing()})
            return out({'caps': app['registry'].listing()})
        if a.cmd == 'learned':
            return out(app['learning'].listing())
        if a.cmd == 'meta':
            return out({'metacognition': app['learning'].metacognition()})
        if a.cmd == 'forget':
            if a.kind == 'memory':
                return out(app['brain'].retract(a.ident))
            return out(app['learning'].retract(a.kind, int(a.ident)))
        if a.cmd == 'doctor':
            return cmd_doctor(app, cfg, a)
        if a.cmd == 'kill':
            f = (Path(cfg['system_db']).parent if a.glob else app['state']) / 'KILL'
            if a.state == 'on':
                f.write_text(time.strftime('%Y-%m-%d %H:%M:%S Not-Aus\n'))
            else:
                f.unlink(missing_ok=True)
            return out({'kill': a.state, 'scope': 'global' if a.glob else cfg['identity'], 'file': str(f)})
        if a.cmd == 'pc-lease':
            if global_kill(cfg) or (app['state'] / 'KILL').exists():
                return out({'lease': None, 'why': 'kill switch'})
            req, _ = read_stdin_request()
            caps = [c for c in (req.get('caps') or []) if isinstance(c, str)][:20]
            return out({'lease': eng.pc_lease(caps, str(req.get('worker') or 'pc')[:40])})
        if a.cmd == 'pc-pull':
            sys.stdout.buffer.write(eng.workspace_tar(a.job))
            return 0
        if a.cmd == 'pc-push':
            data = sys.stdin.buffer.read(500_000_000)
            return out(eng.pc_complete(a.job, a.step, bool(a.ok), a.detail, data if data else None))
        if a.cmd == 'pc-report':
            req, _ = read_stdin_request()
            return out({'reported': app['registry'].report_pc(req.get('caps') or {})})
    except PermissionError as e:
        return out({'error': str(e)}, 3)
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        return out({'error': f'{type(e).__name__}: {e}'}, 2)
    except Exception as e:  # noqa: BLE001
        return out({'error': f'{type(e).__name__}: {e}'}, 1)
    return out({'error': 'unknown command'}, 2)


if __name__ == '__main__':
    sys.exit(main())
