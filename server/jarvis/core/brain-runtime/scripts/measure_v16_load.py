#!/usr/bin/env python3
"""V16 load measurement on the real server (Gate F). Read-only, stdlib only.

Samples every N seconds: CPU busy/iowait, PSI cpu/mem/io (exact stall share per interval from the PSI totals),
MemAvailable, swap used and swap-in/out, major faults, disk throughput and utilisation per disk, temperatures,
load, the CPU/RSS of the JARVIS process tree (every `jarvis_cli.py tick` and all its children: claude, bwrap,
tools), and the response time of the local services (HTTP without following redirects, TCP connect, DNS, unix
socket). Prints one JSON summary (mean / median / p95 / p99 / max per metric); --raw writes every sample as JSONL
so several windows can be pooled later (analyse_v16_load.py).

  python3 measure_v16_load.py --seconds 300 --every 3 --label idle-1 --raw idle-1.jsonl
  python3 measure_v16_load.py --seconds 1800 --min-seconds 300 --stop-file STOP --label load-1 --raw load-1.jsonl
Without --probe the MA-Server default probes are used; --probe NAME=URL adds/replaces one
(http://host:port/path, tcp:host:port, dns:host:port, unix:/path).
"""
import argparse
import http.client
import json
import math
import os
import socket
import statistics
import struct
import time

DEFAULT_PROBES = {
    'homeassistant': 'http://127.0.0.1:8123/',
    'portal': 'http://127.0.0.1:18081/',
    'authelia': 'http://127.0.0.1:19091/',
    'caddy_http': 'http://127.0.0.1:80/',
    'couchdb': 'http://127.0.0.1:15984/',
    'navidrome': 'http://127.0.0.1:4533/',
    'ttyd': 'http://127.0.0.1:7681/',
    'web_12586': 'http://127.0.0.1:12586/',
    'api_18765': 'http://127.0.0.1:18765/',
    'postgres': 'tcp:127.0.0.1:5432',
    'dns_blocky': 'dns:192.168.0.111:53',
}
DISKS = ('sda', 'sdb')
TIMEOUT = 3.0


# ---------- system counters ----------
def cpu_times():
    v = [int(x) for x in open('/proc/stat').readline().split()[1:]]
    return sum(v), v[3] + v[4], v[4]  # total, idle+iowait, iowait


def psi_totals(kind):
    """(some_total_us, full_total_us) or None."""
    try:
        some = full = None
        for line in open(f'/proc/pressure/{kind}'):
            tot = int(line.split('total=')[1])
            if line.startswith('some'):
                some = tot
            elif line.startswith('full'):
                full = tot
        return some, full
    except (OSError, IndexError, ValueError):
        return None


def meminfo():
    d = {}
    for line in open('/proc/meminfo'):
        k, v = line.split(':', 1)
        d[k] = int(v.split()[0])
    return d


def vmstat():
    want = ('pswpin', 'pswpout', 'pgmajfault')
    d = {}
    for line in open('/proc/vmstat'):
        k, v = line.split()
        if k in want:
            d[k] = int(v)
    return d


def diskstats():
    d = {}
    for line in open('/proc/diskstats'):
        p = line.split()
        if p[2] in DISKS:  # sectors read, sectors written, io_ticks (ms busy)
            d[p[2]] = (int(p[5]), int(p[9]), int(p[12]))
    return d


def temperatures():
    t = {}
    base = '/sys/class/thermal'
    try:
        for z in sorted(os.listdir(base)):
            if z.startswith('thermal_zone'):
                try:
                    name = open(f'{base}/{z}/type').read().strip()
                    t[f'{name}_{z[12:]}'] = int(open(f'{base}/{z}/temp').read()) / 1000
                except (OSError, ValueError):
                    pass
    except OSError:
        pass
    base = '/sys/class/hwmon'
    try:
        for h in sorted(os.listdir(base)):
            try:
                if open(f'{base}/{h}/name').read().strip() != 'coretemp':
                    continue
                for f in sorted(os.listdir(f'{base}/{h}')):
                    if f.startswith('temp') and f.endswith('_input'):
                        t[f'coretemp_{f[4:-6]}'] = int(open(f'{base}/{h}/{f}').read()) / 1000
            except (OSError, ValueError):
                pass
    except OSError:
        pass
    return t


def proc_table():
    """pid -> (ppid, cpu_ticks, rss_pages, is_tick_root)."""
    tab = {}
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        try:
            st = open(f'/proc/{pid}/stat').read().rsplit(')', 1)[1].split()
            root = False
            if st[0] != 'Z':
                cmd = open(f'/proc/{pid}/cmdline', 'rb').read()
                root = b'jarvis_cli.py' in cmd and b'\x00tick' in cmd
            tab[int(pid)] = (int(st[1]), int(st[11]) + int(st[12]), int(st[21]), root)
        except (OSError, IndexError, ValueError):
            continue
    return tab


def jarvis_tree(tab):
    kids = {}
    for pid, (ppid, *_r) in tab.items():
        kids.setdefault(ppid, []).append(pid)
    todo = [p for p, v in tab.items() if v[3]]
    seen = set()
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.add(p)
        todo.extend(kids.get(p, ()))
    return seen


# ---------- service probes ----------
def probe(target):
    """Response time in ms (None = no answer/error) and a short result code."""
    t = time.monotonic()
    try:
        if target.startswith('http://'):
            hostport, _, path = target[7:].partition('/')
            host, _, port = hostport.partition(':')
            c = http.client.HTTPConnection(host, int(port or 80), timeout=TIMEOUT)
            try:
                c.request('GET', '/' + path, headers={'User-Agent': 'jarvis-measure'})
                r = c.getresponse()
                r.read(2048)
                code = str(r.status)  # any HTTP status (also 3xx/401) proves the service answered; no redirect is followed
            finally:
                c.close()
        elif target.startswith('tcp:'):
            host, port = target[4:].rsplit(':', 1)
            socket.create_connection((host, int(port)), timeout=TIMEOUT).close()
            code = 'connect'
        elif target.startswith('unix:'):
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(TIMEOUT)
            try:
                s.connect(target[5:])
            finally:
                s.close()
            code = 'connect'
        elif target.startswith('dns:'):
            host, port = target[4:].rsplit(':', 1)
            qid = os.getpid() & 0xFFFF
            q = struct.pack('>HHHHHH', qid, 0x0100, 1, 0, 0, 0) + b'\x07example\x03com\x00' + struct.pack('>HH', 1, 1)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(TIMEOUT)
            try:
                s.sendto(q, (host, int(port)))
                data = s.recv(512)
            finally:
                s.close()
            code = f'rcode{data[3] & 0x0F}' if len(data) > 3 else 'short'
        else:
            return None, 'bad-target'
    except Exception as e:  # noqa: BLE001 - every failure counts as "no answer"
        return None, type(e).__name__
    return round((time.monotonic() - t) * 1000, 2), code


# ---------- statistics ----------
def pct(xs, q):
    """Nearest-rank percentile on sorted data."""
    return xs[max(0, min(len(xs) - 1, math.ceil(q / 100 * len(xs)) - 1))]


def summary(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    return {'mean': round(statistics.fmean(xs), 2), 'median': round(statistics.median(xs), 2),
            'p95': round(pct(xs, 95), 2), 'p99': round(pct(xs, 99), 2), 'max': round(xs[-1], 2), 'n': len(xs)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seconds', type=int, default=180, help='hard upper limit of the window')
    ap.add_argument('--min-seconds', type=int, default=0, help='with --stop-file: never stop before this')
    ap.add_argument('--stop-file', help='end the window early once this file exists (and --min-seconds passed)')
    ap.add_argument('--every', type=float, default=5)
    ap.add_argument('--label', default='run')
    ap.add_argument('--raw', help='write every sample as one JSON line')
    ap.add_argument('--probe', action='append', default=[], help='NAME=TARGET')
    ap.add_argument('--no-default-probes', action='store_true')
    a = ap.parse_args()
    probes = {} if a.no_default_probes else dict(DEFAULT_PROBES)
    for p in a.probe:
        k, _, v = p.partition('=')
        probes[k] = v
    hz = os.sysconf('SC_CLK_TCK')
    page_kb = os.sysconf('SC_PAGE_SIZE') // 1024
    raw = open(a.raw, 'w') if a.raw else None

    prev_cpu, prev_vm, prev_disk = cpu_times(), vmstat(), diskstats()
    prev_psi = {k: psi_totals(k) for k in ('cpu', 'memory', 'io')}
    prev_tab = proc_table()
    prev_t = time.monotonic()
    t_start = prev_t
    samples = []
    codes = {}
    while True:
        time.sleep(a.every)
        now = time.monotonic()
        dt = now - prev_t
        s = {'ts': round(time.time(), 2), 'label': a.label}
        cur = cpu_times()
        dtot = max(cur[0] - prev_cpu[0], 1)
        s['cpu_busy'] = round(100 * (1 - (cur[1] - prev_cpu[1]) / dtot), 2)
        s['iowait'] = round(100 * (cur[2] - prev_cpu[2]) / dtot, 2)
        prev_cpu = cur
        for k in ('cpu', 'memory', 'io'):
            p = psi_totals(k)
            if p and prev_psi[k]:
                s[f'psi_{k}_some'] = round((p[0] - prev_psi[k][0]) / (dt * 1e4), 2)  # µs stalled / interval -> %
                if p[1] is not None and prev_psi[k][1] is not None:
                    s[f'psi_{k}_full'] = round((p[1] - prev_psi[k][1]) / (dt * 1e4), 2)
            prev_psi[k] = p
        m = meminfo()
        s['mem_avail_mb'] = m['MemAvailable'] // 1024
        s['swap_used_mb'] = (m['SwapTotal'] - m['SwapFree']) // 1024
        vm = vmstat()
        s['swap_in_kbs'] = round((vm['pswpin'] - prev_vm['pswpin']) * page_kb / dt, 1)
        s['swap_out_kbs'] = round((vm['pswpout'] - prev_vm['pswpout']) * page_kb / dt, 1)
        s['majfault_s'] = round((vm['pgmajfault'] - prev_vm['pgmajfault']) / dt, 1)
        prev_vm = vm
        dk = diskstats()
        for d, (rs, ws, busy) in dk.items():
            if d in prev_disk:
                s[f'{d}_read_kbs'] = round((rs - prev_disk[d][0]) / 2 / dt, 1)
                s[f'{d}_write_kbs'] = round((ws - prev_disk[d][1]) / 2 / dt, 1)
                s[f'{d}_util'] = round(min(100.0, (busy - prev_disk[d][2]) / (dt * 10)), 1)
        prev_disk = dk
        temps = temperatures()
        s['temp_max_c'] = max(temps.values()) if temps else None
        s['temp_coretemp_c'] = max((v for k, v in temps.items() if k.startswith('coretemp')), default=None)
        s['load1'] = round(os.getloadavg()[0], 2)
        tab = proc_table()
        tree = jarvis_tree(tab)
        jticks = 0
        for pid in tree:
            before = prev_tab.get(pid)
            jticks += tab[pid][1] - (before[1] if before and before[0] == tab[pid][0] else 0)
        s['jarvis_cpu_pct'] = round(100 * jticks / hz / dt, 1)  # % of ONE core (server has 2)
        s['jarvis_rss_mb'] = round(sum(tab[p][2] for p in tree) * page_kb / 1024, 1)
        s['jarvis_procs'] = len(tree)
        prev_tab = tab
        for name, target in probes.items():
            ms, code = probe(target)
            s[f'lat_{name}'] = ms
            codes.setdefault(name, {}).setdefault(code, 0)
            codes[name][code] += 1
        prev_t = now
        samples.append(s)
        if raw:
            raw.write(json.dumps(s) + '\n')
            raw.flush()
        el = time.monotonic() - t_start
        if el >= a.seconds or (a.stop_file and os.path.exists(a.stop_file) and el >= a.min_seconds):
            break
    if raw:
        raw.close()
    keys = [k for k in samples[0] if k not in ('ts', 'label')] if samples else []
    out = {'label': a.label, 'seconds': round(time.monotonic() - t_start), 'every_s': a.every, 'samples': len(samples),
           'metrics': {k: summary([x.get(k) for x in samples]) for k in keys if not k.startswith('lat_')},
           'latency_ms': {k[4:]: summary([x.get(k) for x in samples]) for k in keys if k.startswith('lat_')},
           'latency_failures': {k[4:]: sum(1 for x in samples if x.get(k) is None) for k in keys if k.startswith('lat_')},
           'probe_results': codes,
           'note': 'jarvis_cpu_pct = % of one core over the interval (2 cores = 200 %); processes that end inside an '
                   'interval lose their last partial interval; psi_* = exact stall share per interval from PSI totals'}
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
