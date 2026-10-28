#!/usr/bin/env python3
"""Basis-GO-Prüfung (Referenzanalyse 28.10.2026): echte, wiederholbare Proben statt Behauptungen. Druckt nur Zählwerte,
nie Geheimnisse. Aufruf als root (liest die Geheimnisdateien, um zu prüfen, dass ihre WERTE nirgends in Logs/DBs stehen):
  sudo python3 basis_go_check.py --user andrew
Teile, die nur der Owner prüfen kann (echtes Handy, echte Stimme), werden als OFFEN ausgewiesen, nie als bestanden."""
import argparse
import glob
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path

HOME = Path('/home/andrew')
STATE = Path('/srv/ma-home/library/.jarvis/v16/philipp')
CLI = HOME / '.local/share/ma-jarvis/current/brain-runtime/jarvis_cli.py'
CFG = HOME / '.config/ma-jarvis/jarvis.json'


def secrets() -> dict:
    """name -> Wert (nur im Speicher). Quellen: bekannte Token-/Schlüsseldateien des Systems."""
    out = {}
    try:
        out['portal_proxy_key'] = json.load(open('/etc/ma-home/portal.json'))['proxy_key']
    except (OSError, KeyError, ValueError):
        pass
    for name, path in (('voice_token', HOME / '.config/ma-jarvis/voice-token'), ('kuma_bridge_token', HOME / '.config/ma-jarvis/kuma-bridge-token'),
                       ('kuma_push_token', HOME / '.config/ma-jarvis/kuma-pc-push')):
        try:
            v = path.read_text().strip()
            if v:
                out[name] = v
        except OSError:
            pass
    try:
        cf = json.load(open(CFG)).get('cloud_fallback') or {}
        if cf.get('key_file'):
            v = Path(cf['key_file']).read_text().strip()
            if v:
                out['cloud_api_key'] = v
    except (OSError, ValueError):
        pass
    return {k: v for k, v in out.items() if len(v) >= 12}


def scan_text(blob: str, sec: dict) -> dict:
    return {k: blob.count(v) for k, v in sec.items() if v in blob}


def leak_scan(sec: dict) -> dict:
    res = {}
    for db in (STATE / 'brain.db', STATE.parent / 'system.db'):
        try:
            c = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
            blob = []
            for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
                cols = [r[1] for r in c.execute(f'PRAGMA table_info("{t}")') if r[2].upper() in ('TEXT', '')]
                for col in cols:
                    for (v,) in c.execute(f'SELECT "{col}" FROM "{t}"'):
                        if isinstance(v, str):
                            blob.append(v)
            res[str(db)] = scan_text('\n'.join(blob), sec)
        except sqlite3.Error as e:
            res[str(db)] = {'error': str(e)[:80]}
    logs = glob.glob(str(HOME / '.local/state/ma-jarvis/*.log')) + glob.glob(str(HOME / '.local/state/ma-jarvis/*.err'))
    for f in logs:
        try:
            res[f] = scan_text(Path(f).read_text(errors='replace'), sec)
        except OSError:
            pass
    for unit in ('ma-claude-bridge', 'ma-home-web', 'ma-kuma-signal', 'ma-jarvis-signal', 'jarvis-watchdog'):
        try:
            j = subprocess.run(['journalctl', '-u', unit, '--since', '-14d', '--no-pager', '-o', 'cat'], capture_output=True, text=True,
                               timeout=60).stdout
            res['journal:' + unit] = scan_text(j, sec)
        except (OSError, subprocess.SubprocessError):
            res['journal:' + unit] = {'error': 'nicht lesbar'}
    hits = {k: v for k, v in res.items() if v and 'error' not in v}
    return {'sources': len(res), 'secrets_checked': sorted(sec), 'hits': {k: sum(v.values()) for k, v in hits.items()}}


def restore_drill() -> dict:
    """Neueste Sicherung praktisch wiederherstellen (in ein Wegwerf-Verzeichnis), prüfen, mit Live vergleichen."""
    backs = sorted(glob.glob(str(HOME / '.local/share/ma-jarvis/backups/*')), reverse=True)
    for b in backs:
        cand = [p for p in Path(b).rglob('brain*.db')]
        if cand:
            break
    else:
        return {'ok': False, 'why': 'keine Sicherung mit brain.db gefunden'}
    tmp = Path(tempfile.mkdtemp(prefix='restore-drill-'))
    try:
        dst = tmp / 'brain.db'
        shutil.copy2(cand[0], dst)
        c = sqlite3.connect(dst)
        integ = c.execute('PRAGMA integrity_check').fetchone()[0]
        n_backup = c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
        last = c.execute('SELECT id, state FROM jobs ORDER BY created DESC LIMIT 1').fetchone()
        c.close()
        live = sqlite3.connect(f'file:{STATE / "brain.db"}?mode=ro', uri=True)
        n_live = live.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
        same = live.execute('SELECT state FROM jobs WHERE id=?', (last[0],)).fetchone() if last else None
        return {'ok': integ == 'ok' and n_backup <= n_live and bool(same), 'backup': b, 'integrity': integ, 'jobs_backup': n_backup,
                'jobs_live': n_live, 'last_job_in_backup': last[0] if last else None, 'found_in_live': bool(same)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cli(*args, user='andrew'):
    p = subprocess.run(['sudo', '-u', user, '/usr/bin/python3', str(CLI), '--config', str(CFG), *args], capture_output=True, text=True, timeout=120)
    try:
        return p.returncode, json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return p.returncode, {'raw': p.stdout[-300:], 'err': p.stderr[-300:]}


def kill_drill() -> dict:
    """Not-Aus live: nur wenn kein Auftrag aktiv. Stufe exec setzen -> Takt muss untätig bleiben -> wieder aus."""
    live = sqlite3.connect(f'file:{STATE / "brain.db"}?mode=ro', uri=True)
    active = live.execute("SELECT COUNT(*) FROM jobs WHERE state NOT IN ('done','partial','failed','cancelled')").fetchone()[0]
    if active:
        return {'ok': None, 'why': f'{active} aktive Aufträge - Probe ausgelassen'}
    t0 = time.monotonic()
    rc_on, on = cli('kill', 'on', '--level', 'exec')
    for _ in range(8):   # Cron-Takt hält evtl. gerade die Sperre
        rc_t, tick = cli('tick', '--max-seconds', '5')
        if 'another tick' not in str(tick.get('idle', '')):
            break
        time.sleep(4)
    rc_off, off = cli('kill', 'off')
    return {'ok': rc_on == 0 and 'kill switch' in str(tick.get('idle', '')) and rc_off == 0, 'tick': tick, 'seconds': round(time.monotonic() - t0, 1),
            'llm_calls': 0}


def recovered_events() -> int:
    c = sqlite3.connect(f'file:{STATE / "brain.db"}?mode=ro', uri=True)
    return c.execute("SELECT COUNT(*) FROM job_events WHERE kind='recovered'").fetchone()[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-kill', action='store_true')
    a = ap.parse_args()
    sec = secrets()
    out = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'leak_scan': leak_scan(sec), 'restore_drill': restore_drill(),
           'kill_drill': None if a.no_kill else kill_drill(), 'recovered_events_live': recovered_events()}
    del sec
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
