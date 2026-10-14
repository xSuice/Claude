#!/usr/bin/env python3
"""V10.1/V11 read-only inventory of the REAL machine before any installation.

Reports OS (incl. ZimaOS / read-only root), hardware, tools, sandbox capability, Claude Code
configuration (hook events + program names only, MCP server names/transports, skills, agents,
plugins), duplicate hooks, router candidates, Obsidian vaults, existing brain data and running
brain processes. Never prints secrets (env values, tokens, hook arguments); changes nothing.
Usage:  python3 server/inventory.py [--vault PATH] > inventory.json
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
from pathlib import Path

HOME = Path.home()


def run(argv, timeout=10):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        return (p.stdout or p.stderr).strip().splitlines()[0][:200] if (p.stdout or p.stderr).strip() else ''
    except (OSError, subprocess.TimeoutExpired):
        return None


def os_info():
    rel = {}
    try:
        for line in Path('/etc/os-release').read_text().splitlines():
            if '=' in line:
                k, v = line.split('=', 1); rel[k] = v.strip('"')
    except OSError:
        pass
    root_ro = None
    try:
        for line in Path('/proc/mounts').read_text().splitlines():
            f = line.split()
            if len(f) > 3 and f[1] == '/':
                root_ro = 'ro' in f[3].split(',')
    except OSError:
        pass
    zima = 'zima' in (rel.get('ID', '') + rel.get('NAME', '')).lower() or Path('/etc/casaos').exists()
    return {'id': rel.get('ID'), 'version': rel.get('VERSION_ID'), 'pretty': rel.get('PRETTY_NAME'),
            'kernel': platform.release(), 'arch': platform.machine(), 'zimaos_or_casaos': zima,
            'root_read_only': root_ro, 'systemd_user': run(['systemctl', '--user', 'is-system-running']) }


def hardware():
    out = {'cpus': os.cpu_count()}
    try:
        out['cpu_model'] = next((l.split(':', 1)[1].strip() for l in Path('/proc/cpuinfo').read_text().splitlines()
                                 if l.startswith(('model name', 'Model'))), None)
        mem = {l.split(':')[0]: int(l.split()[1]) for l in Path('/proc/meminfo').read_text().splitlines() if l.split()[1:2]}
        out['mem_total_mb'] = mem.get('MemTotal', 0) // 1024
        out['mem_available_mb'] = mem.get('MemAvailable', 0) // 1024
    except (OSError, ValueError):
        pass
    disks = {}
    for p in ('/', '/DATA', '/media', str(HOME)):
        try:
            u = shutil.disk_usage(p); disks[p] = {'total_gb': round(u.total / 2**30, 1), 'free_gb': round(u.free / 2**30, 1)}
        except OSError:
            pass
    out['disks'] = disks
    return out


def tools():
    t = {'python': sys.version.split()[0], 'git': run(['git', '--version']), 'node': run(['node', '--version']),
         'claude': run(['claude', '--version']), 'docker': run(['docker', 'version', '--format', '{{.Server.Version}}']),
         'unshare': bool(shutil.which('unshare')), 'sqlite_fts5': None}
    try:
        import sqlite3
        c = sqlite3.connect(':memory:')
        try:
            c.execute('create virtual table t using fts5(a)'); t['sqlite_fts5'] = True
        finally:
            c.close()
    except Exception:  # noqa: BLE001
        t['sqlite_fts5'] = False
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'brain-runtime'))
        import sandbox
        t['brain_sandbox_available'] = sandbox.available()
    except Exception as e:  # noqa: BLE001
        t['brain_sandbox_available'] = f'error: {type(e).__name__}'
    return t


def _load(p):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def claude_config():
    out, dup = {'settings_files': {}, 'mcp_servers': {}, 'skills': [], 'agents': [], 'commands': []}, []
    for f in (HOME / '.claude' / 'settings.json', HOME / '.claude' / 'settings.local.json'):
        d = _load(f)
        if d is None:
            continue
        hooks = {}
        for event, entries in (d.get('hooks') or {}).items():
            progs = []
            for e in entries or []:
                for h in (e.get('hooks') or []):
                    cmd = str(h.get('command', '')).strip()
                    prog = Path(cmd.split()[0]).name if cmd else h.get('type')
                    script = next((Path(x).name for x in cmd.split()[1:] if x.endswith(('.py', '.ps1', '.sh', '.js'))), '')
                    progs.append(f'{prog} {script}'.strip())
            hooks[event] = progs
            dup += [f'{event}: {p}' for p in set(progs) if progs.count(p) > 1]
        out['settings_files'][f.name] = {'hooks': hooks, 'plugins': sorted((d.get('enabledPlugins') or {}).keys()),
                                         'permission_keys': sorted((d.get('permissions') or {}).keys()),
                                         'model': d.get('model')}
    cj = _load(HOME / '.claude.json') or {}
    servers = dict(cj.get('mcpServers') or {})
    for proj in (cj.get('projects') or {}).values():
        servers.update({f"(project) {k}": v for k, v in (proj.get('mcpServers') or {}).items()})
    out['mcp_servers'] = {k: (v.get('type') or ('stdio' if v.get('command') else '?')) for k, v in servers.items()}
    for name, key in (('skills', 'skills'), ('agents', 'agents'), ('commands', 'commands')):
        d = HOME / '.claude' / key
        if d.is_dir():
            out[name] = sorted(p.stem if p.is_file() else p.name for p in d.iterdir() if not p.name.startswith('.'))
    out['claude_md'] = (HOME / '.claude' / 'CLAUDE.md').exists()
    out['duplicate_hooks'] = sorted(set(dup))
    return out


def find(names, roots, depth=4, want_dir=None):
    hits = []
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        base = len(root.parts)
        for d, dirs, files in os.walk(root):
            if len(Path(d).parts) - base >= depth:
                dirs[:] = []
            dirs[:] = [x for x in dirs if x not in ('node_modules', '.git', '.cache', 'proc')]
            for n in (dirs if want_dir else files) + ([] if want_dir is None else []):
                if any(k in n.lower() for k in names):
                    hits.append(str(Path(d) / n))
            if want_dir is None:
                hits += [str(Path(d) / n) for n in dirs if any(k in n.lower() for k in names)]
            if len(hits) > 40:
                return hits
    return sorted(set(hits))


def brain_state():
    out = {'files': [], 'processes': []}
    for d in (HOME / '.local' / 'state' / 'ma-home-brain', HOME / '.config' / 'ma-home-brain'):
        if d.is_dir():
            for f in d.iterdir():
                st = f.stat()
                out['files'].append({'path': str(f), 'bytes': st.st_size, 'mode': oct(stat.S_IMODE(st.st_mode))})
    me = os.getuid()
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            try:
                if p.stat().st_uid != me:
                    continue
                argv = [x.decode(errors='replace') for x in (p / 'cmdline').read_bytes().split(b'\0') if x]
            except OSError:
                continue
            script = next((Path(x).name for x in argv[1:3] if x.endswith('.py')), '')
            if script in ('daemon.py', 'mcp_server.py', 'mcp_server_v5.py', 'supervisor.py', 'executive.py'):
                out['processes'].append({'pid': int(p.name), 'script': script, 'args': argv[-1][:40]})
    return out


def laptop(sysfs=Path('/sys'), proc=Path('/proc')):
    """V11: the laptop IS the server - what limits it (read-only, no root needed)."""
    def rd(p):
        try:
            return p.read_text().strip()
        except OSError:
            return None
    out = {'psi': (proc / 'pressure' / 'cpu').exists(), 'swap': [], 'disks': {}, 'thermal_zones': [], 'power': [],
           'cpufreq_governor': rd(sysfs / 'devices/system/cpu/cpu0/cpufreq/scaling_governor')}
    for line in (rd(proc / 'swaps') or '').splitlines()[1:]:
        f = line.split()
        if len(f) >= 4:
            out['swap'].append({'type': f[1], 'size_mb': int(f[2]) // 1024})
    for b in sorted((sysfs / 'block').glob('*')) if (sysfs / 'block').exists() else []:
        if b.name.startswith(('loop', 'ram', 'zram', 'dm-')):
            continue
        out['disks'][b.name] = {'rotational': rd(b / 'queue/rotational') == '1', 'scheduler': rd(b / 'queue/scheduler')}
    for z in sorted((sysfs / 'class/thermal').glob('thermal_zone*')) if (sysfs / 'class/thermal').exists() else []:
        t = rd(z / 'temp')
        out['thermal_zones'].append({'type': rd(z / 'type'), 'temp_c': int(t) / 1000 if t and t.lstrip('-').isdigit() else None})
    for ps in sorted((sysfs / 'class/power_supply').glob('*')) if (sysfs / 'class/power_supply').exists() else []:
        out['power'].append({'name': ps.name, 'type': rd(ps / 'type'), 'online': rd(ps / 'online'),
                             'capacity': rd(ps / 'capacity'), 'status': rd(ps / 'status')})
    out['on_battery'] = any(p['type'] == 'Battery' and p['status'] == 'Discharging' for p in out['power'])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--vault', action='append', default=[])
    a = ap.parse_args()
    vaults = [str(Path(v).expanduser()) for v in a.vault] or \
        [str(Path(p).parent) for p in find(['.obsidian'], [HOME], depth=3, want_dir=True)]
    rep = {'os': os_info(), 'hardware': hardware(), 'laptop': laptop(), 'tools': tools(), 'claude_code': claude_config(),
           'router_candidates': find(['router'], [HOME / '.claude', HOME / '.router', HOME / '.llm-router',
                                                  HOME / '.config'], depth=3),
           'obsidian_vaults': vaults, 'brain': brain_state(),
           'note': 'read-only inventory; hook arguments, env values and tokens are deliberately not shown'}
    print(json.dumps(rep, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
