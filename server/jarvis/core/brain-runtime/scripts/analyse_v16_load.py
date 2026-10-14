#!/usr/bin/env python3
"""Pools the windows of one or more loadtest_v16.sh runs and judges whether JARVIS impairs the other services.

  python analyse_v16_load.py RUN_DIR [RUN_DIR ...] --out bericht.md [--json summary.json]

Conditions:  off = cron tick removed | idle = tick active, no job | load = whole load window |
             active = samples while a job was running (started..finished) | load2 = two jobs submitted together
Statistics per condition: mean, median, p95, p99, max, n (pooled samples) and the spread of the per-window medians.
Differences active - idle with a moving-block bootstrap 95 % interval (blocks of 10 samples = 30 s, because
neighbouring samples are correlated). The thresholds below were fixed BEFORE the load windows ran (git history).
"""
import argparse
import glob
import json
import math
import os
import random
import statistics

# ---- pre-registered criteria (2026-10-14, before the load data existed) -------------------------------------------
CRIT = {
    'lat_p95_factor': 1.5,      # service p95 under load <= max(1.5 x idle p95, idle p95 + 50 ms)
    'lat_p95_abs_ms': 50.0,
    'ha_p99_ms': 500.0,         # Home Assistant p99 under load
    'mem_avail_min_mb': 600,    # = JARVIS min_mem_mb
    'psi_mem_full_p95': 1.0,    # % of time all tasks stalled on memory
    'swap_in_p95_kbs': 100.0,
    'psi_io_full_p95': 10.0,
    'temp_max_c': 85.0,         # Celeron N2840 Tj,max is 105 C
    'cron_cpu_mean_pct': 2.0,   # idle tick cost, % of one core
}
KEY_METRICS = ['cpu_busy', 'iowait', 'load1', 'psi_cpu_some', 'psi_memory_some', 'psi_memory_full', 'psi_io_some',
               'psi_io_full', 'mem_avail_mb', 'swap_used_mb', 'swap_in_kbs', 'swap_out_kbs', 'majfault_s', 'sda_read_kbs',
               'sda_write_kbs', 'sda_util', 'temp_max_c', 'temp_coretemp_c', 'jarvis_cpu_pct', 'jarvis_rss_mb', 'jarvis_procs']


def pct(xs, q):
    return xs[max(0, min(len(xs) - 1, math.ceil(q / 100 * len(xs)) - 1))]


def stats(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    return {'mean': statistics.fmean(xs), 'median': statistics.median(xs), 'p95': pct(xs, 95), 'p99': pct(xs, 99),
            'max': xs[-1], 'n': len(xs)}


def block_boot(a, b, fn, n=2000, block=10, seed=1):
    """95 % interval of fn(b) - fn(a) with moving-block bootstrap over each sample series."""
    a = [x for x in a if x is not None]
    b = [x for x in b if x is not None]
    if len(a) < block or len(b) < block:
        return None
    rnd = random.Random(seed)

    def res(xs):
        out = []
        while len(out) < len(xs):
            i = rnd.randrange(0, len(xs) - block + 1)
            out.extend(xs[i:i + block])
        return sorted(out[:len(xs)])
    d = sorted(fn(res(b)) - fn(res(a)) for _ in range(n))
    return d[int(0.025 * n)], d[int(0.975 * n) - 1]


def load_runs(dirs):
    windows = []
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, '*.jsonl'))):
            label = os.path.basename(f)[:-6]
            kind = label.split('-', 1)[1]
            rows = [json.loads(x) for x in open(f, encoding='utf-8') if x.strip()]
            jobs = []
            for sf in glob.glob(os.path.join(d, f'{label}.j*.status.json')):
                s = json.load(open(sf, encoding='utf-8'))
                jobs.append(s)
            windows.append({'run': os.path.basename(os.path.normpath(d)), 'label': label, 'kind': kind, 'rows': rows, 'jobs': jobs})
    return windows


def split(windows):
    cond = {'off': [], 'idle': [], 'load': [], 'active': [], 'load2': [], 'active2': []}
    per_window = {}
    for w in windows:
        k = w['kind']
        ivals = [(j['started'] or j['created'], j['finished'] or 1e12) for j in w['jobs'] if j.get('started') or j.get('created')]
        for r in w['rows']:
            if k in ('off', 'idle'):
                cond[k].append(r)
            elif k in ('load', 'load2'):
                cond[k].append(r)
                if any(a <= r['ts'] <= b for a, b in ivals):
                    cond['active' if k == 'load' else 'active2'].append(r)
        per_window[f"{w['run']}/{w['label']}"] = w
    return cond, per_window


def fmt(v, nd=1):
    return '–' if v is None else (f'{v:.{nd}f}' if isinstance(v, float) else str(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('runs', nargs='+')
    ap.add_argument('--out', required=True)
    ap.add_argument('--json')
    a = ap.parse_args()
    windows = load_runs(a.runs)
    cond, per_window = split(windows)
    lat_keys = sorted({k for w in windows for r in w['rows'] for k in r if k.startswith('lat_')})
    metrics = KEY_METRICS + lat_keys
    summary = {c: {m: stats([r.get(m) for r in rows]) for m in metrics} for c, rows in cond.items() if rows}
    fails = {c: {k[4:]: sum(1 for r in rows if r.get(k) is None) for k in lat_keys} for c, rows in cond.items() if rows}
    win_medians = {}
    for name, w in per_window.items():
        win_medians[name] = {m: (stats([r.get(m) for r in w['rows']]) or {}).get('median') for m in metrics}

    L = ['# JARVIS V16 – Lastmessung (Auswertung)', '',
         f'Läufe: {", ".join(os.path.basename(os.path.normpath(r)) for r in a.runs)}. Abtastung alle 3 s.', '',
         '## Fenster', '', '| Fenster | Art | Proben | Aufträge (Zustand, Dauer, Claude-Aufrufe, neue Token) |', '|---|---|---|---|']
    for name, w in per_window.items():
        js = '; '.join(f"{j['id']} {j['state']}, {((j['finished'] or 0) - (j['started'] or j['created']))} s, "
                       f"{j['claude_calls']} Aufrufe, {j['tokens_new']} Token" for j in w['jobs']) or '–'
        L.append(f"| {name} | {w['kind']} | {len(w['rows'])} | {js} |")
    L += ['', 'Bedingungen: off = Takt entfernt; idle = Takt aktiv, kein Auftrag; load = ganzes Lastfenster; '
          'active = nur Proben, während ein Auftrag lief; load2/active2 = zwei Aufträge gleichzeitig eingereicht.', '']

    def table(title, ms, nd=1):
        L.extend([f'### {title}', '', '| Messgröße | Bedingung | Mittel | Median | p95 | p99 | Max | n |', '|---|---|---|---|---|---|---|---|'])
        for m in ms:
            for c in ('off', 'idle', 'active', 'active2', 'load'):
                s = summary.get(c, {}).get(m)
                if s:
                    L.append(f"| {m} | {c} | {fmt(s['mean'], nd)} | {fmt(s['median'], nd)} | {fmt(s['p95'], nd)} | "
                             f"{fmt(s['p99'], nd)} | {fmt(s['max'], nd)} | {s['n']} |")
        L.append('')
    L.append('## System')
    L.append('')
    table('CPU, Last, Druck (PSI in % der Zeit)', ['cpu_busy', 'iowait', 'load1', 'psi_cpu_some', 'psi_memory_some',
                                                   'psi_memory_full', 'psi_io_some', 'psi_io_full'])
    table('Speicher und Swap', ['mem_avail_mb', 'swap_used_mb', 'swap_in_kbs', 'swap_out_kbs', 'majfault_s'], 0)
    table('Festplatte sda (HDD) und Temperatur', ['sda_read_kbs', 'sda_write_kbs', 'sda_util', 'temp_max_c', 'temp_coretemp_c'])
    table('JARVIS-Prozessbaum (CPU in % EINES Kerns, 2 Kerne)', ['jarvis_cpu_pct', 'jarvis_rss_mb', 'jarvis_procs'])
    L.append('## Antwortzeiten der Dienste (ms)')
    L.append('')
    table('Dienste', lat_keys, 1)
    L += ['Fehlgeschlagene Proben (keine Antwort in 3 s): ' + '; '.join(
        f"{c}: " + ', '.join(f'{k}={v}' for k, v in f.items() if v) if any(f.values()) else f'{c}: keine'
        for c, f in fails.items()), '']

    # ---- differences with bootstrap intervals
    L += ['## Unterschiede active − idle (95 %-Intervall, Block-Bootstrap)', '',
          '| Messgröße | Δ Median | Intervall | Δ p95 | Intervall |', '|---|---|---|---|---|']
    diffs = {}
    for m in ['cpu_busy', 'psi_cpu_some', 'psi_memory_some', 'psi_io_some', 'mem_avail_mb', 'sda_util', 'temp_max_c'] + lat_keys:
        ia = [r.get(m) for r in cond['idle']]
        ac = [r.get(m) for r in cond['active']]
        if not cond['idle'] or not cond['active']:
            continue
        si, sa = stats(ia), stats(ac)
        if not si or not sa:
            continue
        cm = block_boot(ia, ac, statistics.median)
        c95 = block_boot(ia, ac, lambda xs: pct(xs, 95))
        diffs[m] = {'d_median': sa['median'] - si['median'], 'ci_median': cm, 'd_p95': sa['p95'] - si['p95'], 'ci_p95': c95}
        L.append(f"| {m} | {fmt(diffs[m]['d_median'], 2)} | {fmt(cm[0], 2) if cm else '–'} … {fmt(cm[1], 2) if cm else '–'} | "
                 f"{fmt(diffs[m]['d_p95'], 2)} | {fmt(c95[0], 2) if c95 else '–'} … {fmt(c95[1], 2) if c95 else '–'} |")
    L.append('')

    # ---- verdict against the pre-registered criteria
    checks = []
    idle, act = summary.get('idle', {}), summary.get('active', {})
    for k in lat_keys:
        si, sa = idle.get(k), act.get(k)
        if si and sa:
            lim = max(CRIT['lat_p95_factor'] * si['p95'], si['p95'] + CRIT['lat_p95_abs_ms'])
            checks.append((f'{k[4:]}: p95 unter Last {sa["p95"]:.1f} ms ≤ {lim:.1f} ms', sa['p95'] <= lim))
        fi, fa = fails.get('idle', {}).get(k[4:], 0), fails.get('active', {}).get(k[4:], 0)
        if fi == 0:
            checks.append((f'{k[4:]}: keine Ausfälle unter Last ({fa})', fa == 0))
    ha = act.get('lat_homeassistant')
    if ha:
        checks.append((f'Home Assistant p99 unter Last {ha["p99"]:.1f} ms ≤ {CRIT["ha_p99_ms"]:.0f} ms', ha['p99'] <= CRIT['ha_p99_ms']))
    allload = {m: stats([r.get(m) for r in cond['load'] + cond['load2']]) for m in metrics}
    if allload.get('mem_avail_mb'):
        v = min(r.get('mem_avail_mb') for r in cond['load'] + cond['load2'])
        checks.append((f'MemAvailable Minimum unter Last {v} MB ≥ {CRIT["mem_avail_min_mb"]} MB', v >= CRIT['mem_avail_min_mb']))
    for m, key, lim in (('psi_memory_full', 'p95', CRIT['psi_mem_full_p95']), ('swap_in_kbs', 'p95', CRIT['swap_in_p95_kbs']),
                        ('psi_io_full', 'p95', CRIT['psi_io_full_p95']), ('temp_max_c', 'max', CRIT['temp_max_c'])):
        s = allload.get(m)
        if s:
            checks.append((f'{m} {key} unter Last {s[key]:.1f} ≤ {lim}', s[key] <= lim))
    sj = idle.get('jarvis_cpu_pct')
    if sj:
        checks.append((f'Takt im Leerlauf: JARVIS-CPU Mittel {sj["mean"]:.2f} % ≤ {CRIT["cron_cpu_mean_pct"]} % eines Kerns',
                       sj['mean'] <= CRIT['cron_cpu_mean_pct']))
    L += ['## Bewertung gegen die vorab festgelegten Kriterien', '']
    L += [f"- {'ERFÜLLT' if ok else 'NICHT ERFÜLLT'}: {t}" for t, ok in checks]
    L += ['', f"Ergebnis: {sum(ok for _, ok in checks)}/{len(checks)} Kriterien erfüllt.", '',
          '## Grenzen', '',
          '- Proben im 3-s-Takt verpassen kurze Spitzen; p99 beruht je Bedingung auf wenigen Hundert Proben.',
          '- Nachbarproben sind korreliert, deshalb Block-Bootstrap; die Intervalle sind trotzdem nur Näherungen.',
          '- Andere Timer (vault-pg alle 10 min, git-sync alle 15 min, Abgleich PC↔Server) laufen in allen Bedingungen; '
          'die Fenster sind deshalb abwechselnd angeordnet.',
          '- Die Last hängt von den Aufträgen ab (hier kurze Python-/Dokument-Aufträge, Claude rechnet extern). '
          'Schwere lokale Schritte (ffmpeg, LibreOffice) sind nicht abgedeckt.']
    with open(a.out, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(L) + '\n')
    if a.json:
        json.dump({'criteria': CRIT, 'summary': summary, 'failures': fails, 'diffs': diffs, 'window_medians': win_medians,
                   'checks': [{'text': t, 'ok': ok} for t, ok in checks]}, open(a.json, 'w', encoding='utf-8'), indent=1, default=str)
    print(f"{sum(ok for _, ok in checks)}/{len(checks)} Kriterien erfüllt -> {a.out}")


if __name__ == '__main__':
    main()
