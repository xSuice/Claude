#!/usr/bin/env python3
"""V16 load measurement on the real server (Gate F). Samples every N seconds: CPU busy/iowait, PSI cpu/mem/io,
MemAvailable, load, latency of critical local services, and the CPU used by JARVIS processes (cmdline contains
'jarvis_cli.py' or JARVIS_WORKER). Prints one JSON summary (median / p95 / max). Read-only, stdlib only.

  python3 measure_v16_load.py --seconds 180 --every 5 --label baseline --url http://127.0.0.1:8123/ --url http://127.0.0.1:80/
"""
import argparse
import json
import os
import statistics
import time
import urllib.error
import urllib.request


def cpu_times():
    v = [int(x) for x in open('/proc/stat').readline().split()[1:]]
    return sum(v), v[3] + v[4], v[4]  # total, idle+iowait, iowait


def psi(kind):
    try:
        return float(open(f'/proc/pressure/{kind}').readline().split('avg10=')[1].split()[0])
    except (OSError, IndexError, ValueError):
        return None


def mem_avail():
    for line in open('/proc/meminfo'):
        if line.startswith('MemAvailable:'):
            return int(line.split()[1]) // 1024


def jarvis_cpu_ticks():
    tot = 0
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        try:
            cmd = open(f'/proc/{pid}/cmdline', 'rb').read()
            env_hit = False
            if b'claude' in cmd:
                try:
                    env_hit = b'JARVIS_WORKER=1' in open(f'/proc/{pid}/environ', 'rb').read()
                except OSError:
                    pass
            if b'jarvis_cli.py' in cmd or env_hit:
                f = open(f'/proc/{pid}/stat').read().rsplit(')', 1)[1].split()
                tot += int(f[11]) + int(f[12])
        except (OSError, IndexError, ValueError):
            continue
    return tot


def latency(url):
    t = time.monotonic()
    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=5) as r:  # normal TLS verification; the probes are plain http on localhost
            r.read(2048)
    except urllib.error.HTTPError:
        pass
    except Exception:  # noqa: BLE001
        return None
    return round((time.monotonic() - t) * 1000, 1)


def summary(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    return {'median': round(statistics.median(xs), 2), 'p95': round(xs[min(len(xs) - 1, int(len(xs) * 0.95))], 2),
            'max': round(xs[-1], 2), 'n': len(xs)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seconds', type=int, default=180)
    ap.add_argument('--every', type=float, default=5)
    ap.add_argument('--label', default='run')
    ap.add_argument('--url', action='append', default=[])
    a = ap.parse_args()
    hz = os.sysconf('SC_CLK_TCK')
    rows = {k: [] for k in ('cpu_busy', 'iowait', 'psi_cpu', 'psi_mem', 'psi_io', 'mem_avail_mb', 'load1')}
    lat = {u: [] for u in a.url}
    t0, j0 = cpu_times(), jarvis_cpu_ticks()
    jstart, wall0 = j0, time.monotonic()
    end = time.monotonic() + a.seconds
    prev = t0
    while time.monotonic() < end:
        time.sleep(a.every)
        cur = cpu_times()
        dt = max(cur[0] - prev[0], 1)
        rows['cpu_busy'].append(100 * (1 - (cur[1] - prev[1]) / dt))
        rows['iowait'].append(100 * (cur[2] - prev[2]) / dt)
        prev = cur
        rows['psi_cpu'].append(psi('cpu'))
        rows['psi_mem'].append(psi('memory'))
        rows['psi_io'].append(psi('io'))
        rows['mem_avail_mb'].append(mem_avail())
        rows['load1'].append(os.getloadavg()[0])
        for u in a.url:
            lat[u].append(latency(u))
    wall = time.monotonic() - wall0
    jcpu = (jarvis_cpu_ticks() - jstart) / hz
    print(json.dumps({'label': a.label, 'seconds': round(wall), 'every_s': a.every,
                      **{k: summary(v) for k, v in rows.items()},
                      'latency_ms': {u: summary(v) for u, v in lat.items()},
                      'latency_failures': {u: sum(1 for x in v if x is None) for u, v in lat.items()},
                      'jarvis_cpu_s_visible': round(jcpu, 2),
                      'note': 'JARVIS CPU counts only processes alive at both samples; short ticks are measured by tick self_cpu_ms'},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
