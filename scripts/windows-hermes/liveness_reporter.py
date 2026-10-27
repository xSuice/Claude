"""Hermes-Liveness-Reporter (KIMI SOLO 2026-10-27) — laeuft auf dem Windows-PC, fensterlos (pythonw).
Meldet alle 60 s per SSH an ma-server (heartbeat_report.py), welche Hermes-Profile vom Gateway bedient werden.
Gemeldet wird NUR bei nachgewiesener Liveness: Gateway-PID existiert (Startzeit passt nicht noetig), gateway_state == 'running'
und updated_at < 180 s alt. Andernfalls wird nichts gemeldet -> Heartbeats werden stale -> Watchdog erzeugt STALE_AGENT.
Bedeutung des Heartbeats: 'Profil ist erreichbar (Gateway laeuft)', NICHT 'Profil arbeitet gerade'. Log: liveness.log (rotiert)."""
import ctypes
import datetime as dt
import json
import logging
import logging.handlers
import os
import re
import subprocess
import time

HOME = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'hermes')
STATE = os.path.join(HOME, 'gateway_state.json')
LOG = os.path.join(HOME, 'heartbeat', 'liveness.log')
INTERVAL = 60
MAX_AGE_S = 180
HANDLE = re.compile(r'^(jarvis-[a-z0-9-]+|kimi-supervisor)$')      # 'default' bewusst nicht
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', 'ma-server']
CREATE_NO_WINDOW = 0x08000000

os.makedirs(os.path.dirname(LOG), exist_ok=True)
log = logging.getLogger('liveness')
log.setLevel(logging.INFO)
h = logging.handlers.RotatingFileHandler(LOG, maxBytes=200_000, backupCount=2, encoding='utf-8')
h.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
log.addHandler(h)


def pid_alive(pid):
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    k = ctypes.windll.kernel32
    hnd = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not hnd:
        return False
    code = ctypes.c_ulong()
    ok = k.GetExitCodeProcess(hnd, ctypes.byref(code))
    k.CloseHandle(hnd)
    return bool(ok) and code.value == 259          # STILL_ACTIVE


def live_profiles():
    """Liste der bedienten Profile oder (None, Grund)."""
    try:
        s = json.load(open(STATE, encoding='utf-8'))
    except Exception as e:                       # noqa: BLE001
        return None, 'state unlesbar: %s' % e
    if s.get('gateway_state') != 'running':
        return None, 'gateway_state=%s' % s.get('gateway_state')
    if not pid_alive(s.get('pid', 0)):
        return None, 'pid %s lebt nicht' % s.get('pid')
    try:
        age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(s['updated_at'])).total_seconds()
    except Exception as e:                       # noqa: BLE001
        return None, 'updated_at ungueltig: %s' % e
    if age > MAX_AGE_S:
        return None, 'state %ds alt' % age
    parked = set((s.get('parked_profiles') or {}).keys()) if isinstance(s.get('parked_profiles'), dict) else set(s.get('parked_profiles') or [])
    return [p for p in s.get('served_profiles', []) if HANDLE.match(p) and p not in parked], None


def push_telemetry():
    """Strikt isolierter Messwert-Push (CPU/RAM/GPU) – Fehler duerfen die Liveness-Meldung nie beeinflussen."""
    global tele_ok
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import pc_telemetry
        r = subprocess.run(SSH + ['python3', '/opt/jarvis/council/telemetry_ingest.py'], input=json.dumps(pc_telemetry.snapshot()),
                           capture_output=True, text=True, timeout=45, creationflags=CREATE_NO_WINDOW)
        good = r.returncode == 0
        if good != tele_ok or not good:
            log.info('Telemetrie %s %s', 'ok' if good else 'FEHLER', r.stderr.strip()[:160])
        tele_ok = good
    except Exception as e:                       # noqa: BLE001
        if tele_ok is not False:
            log.info('Telemetrie Ausnahme: %s', str(e)[:160])
        tele_ok = False


tele_ok = None


def main():
    log.info('Reporter gestartet')
    last_ok = None
    while True:
        try:
            profs, why = live_profiles()
            if profs is None:
                if last_ok is not False:
                    log.info('KEINE Meldung: %s', why)
                last_ok = False
            else:
                r = subprocess.run(SSH + ['python3', '/opt/jarvis/council/heartbeat_report.py'] + profs,
                                   capture_output=True, text=True, timeout=45, creationflags=CREATE_NO_WINDOW)
                good = r.returncode == 0
                if good != last_ok or not good:
                    log.info('Meldung %s: %d Profile | %s %s', 'ok' if good else 'FEHLER', len(profs), r.stdout.strip()[:80], r.stderr.strip()[:160])
                last_ok = good
        except Exception as e:                   # noqa: BLE001
            log.info('Ausnahme: %s', str(e)[:200])
            last_ok = False
        push_telemetry()
        time.sleep(INTERVAL)


if __name__ == '__main__':
    main()
