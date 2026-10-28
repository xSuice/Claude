"""OPS-003 Tiefencheck (alle 30 min per cron, ohne LLM, nur lesend).
Prueft die V16-Engine (brain.db) auf haengende Auftraege und abgelaufene Leases sowie Speicher/Platte und neue Tick-Fehler.
Ergebnis geht als Heartbeat an den Uptime-Kuma-Push-Monitor 'Tiefencheck (30 min)': up = alles ok, down = Befund (-> Signal ueber die Bruecke).
Bleibt der Lauf ganz aus, alarmiert Kuma ebenfalls. Exit 0 = ok, 1 = Befund, 2 = Pruefung selbst gescheitert."""
import json, os, shutil, sqlite3, subprocess, sys, time, urllib.parse, urllib.request

DB = '/srv/ma-home/library/.jarvis/v16/philipp/brain.db'
TICK_ERR = '/home/andrew/.local/state/ma-jarvis/tick.err'
STATE = '/home/andrew/.local/state/ma-jarvis/deepcheck.json'
PUSH = '/home/andrew/.config/ma-jarvis/kuma-deep-push'
ACTIVE = ('queued', 'planning', 'running')          # muessen Fortschritt zeigen
WAITING = ('waiting_approval', 'waiting_pc')        # legitime Wartephasen
STUCK_S, WAIT_S = 30 * 60, 24 * 3600
MIN_MEM_MB, MIN_DISK_PCT = 150, 10
# B1-RESOURCES: 2 Kerne -> Last15 > 3.0 heisst ueber 30 min dauerhaft ueberlastet; Swap > 80 % = Speicherdruck
MAX_LOAD15, MAX_SWAP_PCT = 3.0, 80


def findings(now=None, db=DB, tick_err=TICK_ERR, state=None, mem_mb=None, disk_pct=None,
             load15=None, swap_used_pct=None, oom_kills=None):
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
    if load15 is not None and load15 > MAX_LOAD15:
        out.append('Dauerlast: Last15 %.1f bei 2 Kernen' % load15)
    if swap_used_pct is not None and swap_used_pct > MAX_SWAP_PCT:
        out.append('Swap zu %d %% belegt' % swap_used_pct)
    if oom_kills:
        out.append('earlyoom hat %d Prozess(e) beendet' % oom_kills)
    return out


def count_oom_kills(lines):
    # nur echte Abbrueche ('sending SIGTERM to process 123 ...'), nicht das Start-Banner ('sending SIGTERM when mem avail ...')
    return sum(1 for l in lines if 'sending SIG' in l and ' to process ' in l)


def swap_used_pct(mi):
    tot = mi.get('SwapTotal', 0)
    return 0 if not tot else round(100 * (tot - mi.get('SwapFree', 0)) / tot)


def meminfo():
    out = {}
    with open('/proc/meminfo') as f:
        for line in f:
            k, v = line.split(':', 1)
            out[k] = int(v.split()[0])
    return out


def oom_kills_since(since_ts):
    # nur lesend; andrew ist in Gruppe adm -> Journal lesbar. Fehler = 0 (kein Fehlalarm), Lauf selbst bleibt gueltig
    try:
        r = subprocess.run(['journalctl', '-u', 'earlyoom', '--no-pager', '-o', 'cat', '--since', '@%d' % int(since_ts)],
                           capture_output=True, text=True, timeout=20)
        return count_oom_kills(r.stdout.splitlines())
    except (OSError, subprocess.SubprocessError):
        return 0


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
        now = time.time()
        since = state.get('oom_since', now - 1800)
        f = findings(state=state, mem_mb=mem_available_mb(), disk_pct=100 * du.free // du.total,
                     load15=os.getloadavg()[2], swap_used_pct=swap_used_pct(meminfo()), oom_kills=oom_kills_since(since))
        state['oom_since'] = now
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
