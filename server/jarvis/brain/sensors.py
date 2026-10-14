#!/usr/bin/env python3
"""V8 read-only senses for MA-Home: fixed command allowlist, no shell, no LLM.

Each sensor maps a real system state to a small discrete token (e.g. 'active', 'low',
'stale') so unchanged states deduplicate and deviations become anomalies via
CognitiveLoop. Raw command output and logs are never stored.

Config (admin-owned, chmod 600 on POSIX):
{"project": "ma-home", "sensors": [
  {"id": "nginx",  "type": "systemd",  "unit": "nginx.service", "severity": 4},
  {"id": "immich", "type": "docker",   "container": "immich_server", "expect": "healthy"},
  {"id": "data",   "type": "disk",     "path": "/DATA", "min_free_percent": 10, "severity": 5},
  {"id": "backup", "type": "file_age", "path": "/backups/last-ok", "max_age_hours": 26},
  {"id": "web",    "type": "http",     "url": "http://127.0.0.1:8080/health"}
]}
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN = re.compile(r'^[a-z][a-z0-9_-]{0,31}$')
UNIT = re.compile(r'^[A-Za-z0-9@._:-]{1,120}$')
CONTAINER = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')
SENSOR_ID = re.compile(r'^[a-z0-9][a-z0-9_-]{0,47}$')
DEFAULT_EXPECT = {'systemd': 'active', 'docker': 'healthy', 'disk': 'ok',
                  'file_age': 'fresh', 'http': 'up'}
KIND = {'systemd': 'health', 'docker': 'health', 'disk': 'availability',
        'file_age': 'health', 'http': 'availability'}
KEYS = {'systemd': {'unit', 'user'}, 'docker': {'container'}, 'disk': {'path', 'min_free_percent'},
        'file_age': {'path', 'max_age_hours'}, 'http': {'url', 'timeout'}}
COMMON = {'id', 'type', 'expect', 'severity', 'logs', 'data_class'}  # logs: absolute paths for diagnosis packets
MAX_SENSORS = 40


def _run(argv, timeout=10):
    """Fixed argv only. Minimal environment, no stdin, bounded time and output."""
    env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'LC_ALL': 'C'}
    if 'XDG_RUNTIME_DIR' in os.environ:  # needed for systemctl --user
        env['XDG_RUNTIME_DIR'] = os.environ['XDG_RUNTIME_DIR']
    try:
        p = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                           timeout=timeout, env=env)
        return p.returncode, (p.stdout or '')[:200]
    except FileNotFoundError:
        return 127, ''
    except subprocess.TimeoutExpired:
        return 124, ''


def _token(text, fallback='unknown'):
    t = (text or '').strip().split('\n')[0].strip().lower()
    return t if TOKEN.match(t) else fallback


def validate(cfg: dict) -> dict:
    if not isinstance(cfg, dict) or set(cfg) - {'project', 'sensors'}:
        raise ValueError('sensor config: only "project" and "sensors" allowed')
    if not isinstance(cfg.get('project'), str):
        raise ValueError('sensor config: project required')
    sensors = cfg.get('sensors')
    if not isinstance(sensors, list) or not 1 <= len(sensors) <= MAX_SENSORS:
        raise ValueError(f'sensor config: 1..{MAX_SENSORS} sensors required')
    seen = set()
    for s in sensors:
        typ = s.get('type') if isinstance(s, dict) else None
        if typ not in KEYS:
            raise ValueError('unknown sensor type')
        if set(s) - COMMON - KEYS[typ]:
            raise ValueError(f'unknown keys for {typ} sensor')
        if not isinstance(s.get('id'), str) or not SENSOR_ID.match(s['id']) or s['id'] in seen:
            raise ValueError('sensor id must be unique [a-z0-9_-]')
        seen.add(s['id'])
        sev = s.get('severity', 3)
        if type(sev) is not int or not 1 <= sev <= 5:
            raise ValueError('severity 1..5')
        if 'logs' in s and not (isinstance(s['logs'], list) and len(s['logs']) <= 10 and
                                all(isinstance(x, str) and Path(x).is_absolute() for x in s['logs'])):
            raise ValueError('logs: up to 10 absolute paths')
        if 'expect' in s and not (isinstance(s['expect'], str) and TOKEN.match(s['expect'])):
            raise ValueError('expect must be a short lowercase token')
        if typ == 'systemd' and not (isinstance(s.get('unit'), str) and UNIT.match(s['unit'])):
            raise ValueError('invalid systemd unit')
        if typ == 'docker' and not (isinstance(s.get('container'), str) and CONTAINER.match(s['container'])):
            raise ValueError('invalid container name')
        if typ in ('disk', 'file_age'):
            if not isinstance(s.get('path'), str) or not Path(s['path']).is_absolute():
                raise ValueError('absolute path required')
        if typ == 'disk' and not (type(s.get('min_free_percent', 10)) in (int, float) and 0 < s.get('min_free_percent', 10) < 100):
            raise ValueError('min_free_percent 0..100')
        if typ == 'file_age' and not (type(s.get('max_age_hours', 26)) in (int, float) and 0 < s.get('max_age_hours', 26) <= 8760):
            raise ValueError('max_age_hours 0..8760')
        if typ == 'http':
            u = urllib.parse.urlsplit(s.get('url', ''))
            host = u.hostname or ''
            try:
                loopback = host == 'localhost' or ipaddress.ip_address(host).is_loopback
            except ValueError:
                loopback = False
            if u.scheme not in ('http', 'https') or not loopback:
                raise ValueError('http sensor: loopback URLs only (no outbound requests)')
    return cfg


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def read(sensor: dict, runner=_run, now=None) -> tuple[str, str]:
    """Return (state_token, short_evidence). Never raises for an unavailable system."""
    typ = sensor['type']
    if typ == 'systemd':
        argv = ['systemctl'] + (['--user'] if sensor.get('user') else []) + ['is-active', '--', sensor['unit']]
        code, out = runner(argv)
        state = 'sensor-missing' if code == 127 else 'sensor-timeout' if code == 124 else _token(out)
        return state, f'systemctl is-active {sensor["unit"]} (exit {code})'
    if typ == 'docker':
        fmt = '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}'
        code, out = runner(['docker', 'inspect', '--format', fmt, '--', sensor['container']])
        if code == 127: state = 'sensor-missing'
        elif code == 124: state = 'sensor-timeout'
        elif code != 0: state = 'absent'
        else: state = _token(out)
        return state, f'docker inspect {sensor["container"]} (exit {code})'
    if typ == 'disk':
        try:
            u = shutil.disk_usage(sensor['path'])
        except OSError:
            return 'path-missing', f'disk {sensor["path"]} not readable'
        free = 100.0 * u.free / u.total if u.total else 0.0
        limit = sensor.get('min_free_percent', 10)
        return ('ok' if free >= limit else 'low'), f'disk {sensor["path"]} free {free:.1f}% (min {limit}%)'
    if typ == 'file_age':
        now = time.time() if now is None else now
        try:
            age_h = (now - Path(sensor['path']).stat().st_mtime) / 3600
        except OSError:
            return 'missing', f'file {sensor["path"]} missing'
        limit = sensor.get('max_age_hours', 26)
        return ('fresh' if age_h <= limit else 'stale'), f'file age {age_h:.1f}h (max {limit}h)'
    if typ == 'http':
        opener = urllib.request.build_opener(_NoRedirect, urllib.request.ProxyHandler({}))
        try:
            with opener.open(sensor['url'], timeout=sensor.get('timeout', 5)) as r:
                code = r.status
        except urllib.error.HTTPError as e:
            code = e.code
        except (urllib.error.URLError, OSError, ValueError):
            return 'down', f'GET {sensor["url"]} unreachable'
        return ('up' if 200 <= code < 300 else f'status-{code}'), f'GET {sensor["url"]} -> {code}'
    raise ValueError('unknown sensor type')


def scan(loop, cfg: dict, runner=_run, now=None) -> dict:
    """One bounded pass: ensure admin expectations, observe every sensor once."""
    cfg = validate(cfg)
    project = cfg['project']
    if loop.health(project)['paused']:
        return {'paused': True, 'observed': 0}
    out = []
    for s in cfg['sensors']:
        expected = s.get('expect', DEFAULT_EXPECT[s['type']])
        subject = f'sensor:{s["id"]}'
        loop.ensure_expectation(project, subject, expected, f'sensor config {s["type"]}')
        state, evidence = read(s, runner, now)
        sev = s.get('severity', 3) if state != expected else 1
        r = loop.observe(project, KIND[s['type']], subject, state, evidence, sev)
        out.append({'id': s['id'], 'state': state, 'expected': expected,
                    'recorded': r['recorded'], 'new_anomalies': r['anomalies']})
    return {'paused': False, 'observed': len(out), 'sensors': out,
            'deviations': sum(1 for x in out if x['state'] != x['expected']),
            'claude_calls': 0}


def load(path: Path) -> dict:
    path = Path(path).expanduser().resolve(strict=True)
    if os.name == 'posix' and path.stat().st_mode & 0o022:
        raise PermissionError('sensor config must not be group/world writable')
    return validate(json.loads(path.read_text(encoding='utf-8')))


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from brain_core import Brain
    from cognitive_loop import CognitiveLoop
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--config', type=Path, required=True, help='brain config (identity, state_db)')
    p.add_argument('--sensors', type=Path, required=True)
    a = p.parse_args()
    try:
        conf = json.loads(a.config.resolve(strict=True).read_text(encoding='utf-8'))
        db = Path(conf['state_db']).expanduser()
        if not db.is_absolute(): db = (a.config.resolve().parent / db).resolve()
        loop = CognitiveLoop(Brain(db, conf['identity'], set(conf['allowed_projects'])))
        print(json.dumps(scan(loop, load(a.sensors)), ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, PermissionError) as e:
        print(f'ERROR: {type(e).__name__}: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
