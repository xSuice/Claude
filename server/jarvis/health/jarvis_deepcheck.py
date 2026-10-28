"""OPS-003 Tiefencheck (alle 30 min per cron, ohne LLM, nur lesend).
Prueft die V16-Engine (brain.db) auf haengende Auftraege und abgelaufene Leases sowie Speicher/Platte und neue Tick-Fehler.
Ergebnis geht als Heartbeat an den Uptime-Kuma-Push-Monitor 'Tiefencheck (30 min)': up = alles ok, down = Befund (-> Signal ueber die Bruecke).
Bleibt der Lauf ganz aus, alarmiert Kuma ebenfalls. Exit 0 = ok, 1 = Befund, 2 = Pruefung selbst gescheitert."""
import json, os, shutil, sqlite3, sys, time, urllib.parse, urllib.request

DB = '/srv/ma-home/library/.jarvis/v16/philipp/brain.db'
TICK_ERR = '/home/andrew/.local/state/ma-jarvis/tick.err'
STATE = '/home/andrew/.local/state/ma-jarvis/deepcheck.json'
PUSH = '/home/andrew/.config/ma-jarvis/kuma-deep-push'
ACTIVE = ('queued', 'planning', 'running')          # muessen Fortschritt zeigen
WAITING = ('waiting_approval', 'waiting_pc')        # legitime Wartephasen
STUCK_S, WAIT_S = 30 * 60, 24 * 3600
MIN_MEM_MB, MIN_DISK_PCT = 150, 10


def findings(now=None, db=DB, tick_err=TICK_ERR, state=None, mem_mb=None, disk_pct=None):
    now = time.time() if now is None else now
    state = {} if state is None else state
    out = []
    c = sqlite3.connect('file:%s?mode=ro' % db, uri=True, timeout=10)
    try:
        rows = c.execute("""select j.id, j.state, j.updated, j.lease_until, (select max(ts) from job_events e where e.job_id = j.id)
                            from jobs j where j.state not in ('done','partial','failed','cancelled')""").fetchall()
    finally:
        c.close()
    for jid, st, upd, lease, last_ev in rows:
        last = max(x for x in (upd, last_ev, 0) if x is not None)
        age = now - last
        if st in ACTIVE and age > STUCK_S:
            out.append('Auftrag %s %s ohne Fortschritt seit %d min' % (jid, st, age // 60))
        elif st in WAITING and age > WAIT_S:
            out.append('Auftrag %s wartet seit %d h (%s)' % (jid, age // 3600, st))
        elif st not in ACTIVE + WAITING:
            out.append('Auftrag %s in unbekanntem Zustand %s' % (jid, st))
        if st == 'running' and lease and lease < now - 300:
            out.append('Auftrag %s: Lease seit %d min abgelaufen' % (jid, (now - lease) // 60))
    try:
        size = os.path.getsize(tick_err)
    except OSError:
        size = 0
    if size > state.get('tick_err_size', 0):
        out.append('neue Tick-Fehler (%d Bytes)' % (size - state.get('tick_err_size', 0)))
    state['tick_err_size'] = size
    if mem_mb is not None and mem_mb < MIN_MEM_MB:
        out.append('wenig freier Speicher: %d MB' % mem_mb)
    if disk_pct is not None and disk_pct < MIN_DISK_PCT:
        out.append('Platte fast voll: %d %% frei' % disk_pct)
    return out


def mem_available_mb():
    with open('/proc/meminfo') as f:
        for line in f:
            if line.startswith('MemAvailable:'):
                return int(line.split()[1]) // 1024
    return None


def push(status, msg):
    with open(PUSH, encoding='utf-8') as f:
        tok = f.read().strip()
    if not (tok.isascii() and tok.replace('-', '').replace('_', '').isalnum()):
        raise ValueError('push token format')
    q = urllib.parse.urlencode({'status': status, 'msg': msg[:180]})
    urllib.request.urlopen('http://127.0.0.1:3001/api/push/%s?%s' % (tok, q), timeout=5).read()


def main():
    try:
        state = json.load(open(STATE))
    except (OSError, ValueError):
        state = {}
    try:
        du = shutil.disk_usage('/srv')
        f = findings(state=state, mem_mb=mem_available_mb(), disk_pct=100 * du.free // du.total)
    except Exception as e:  # Pruefung selbst kaputt -> ebenfalls melden
        f, code = ['Tiefencheck gescheitert: %s' % type(e).__name__], 2
    else:
        code = 1 if f else 0
    tmp = STATE + '.tmp'
    with open(tmp, 'w') as fh:
        json.dump(state, fh)
    os.replace(tmp, STATE)
    msg = '; '.join(f) if f else 'OK'
    print(time.strftime('%F %T'), msg, flush=True)
    try:
        push('down' if f else 'up', msg)
    except (OSError, ValueError):
        print('kuma push failed', file=sys.stderr)
    return code


if __name__ == '__main__':
    sys.exit(main())
