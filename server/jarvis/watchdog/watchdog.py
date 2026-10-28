#!/usr/bin/env python3
"""JARVIS Evidence-Watchdog (SPEC-MASTER §7-8, §10): unterscheidet
Arbeitsversprechen von realer Ausführung. Kein LLM. Keine erfundenen Endpunkte.

Adapter:
  engine   (REAL)         - brain.db-Job-Events: nur Tool-/Ausführungs-Events zählen als Fortschritt
  council  (REAL)         - PG heartbeats/tasks: Chat-Nachrichten aktualisieren keinen Fortschritt
  hermes   (MONITOR_ONLY) - via council-Heartbeats beobachtet; keine direkte Schnittstelle

Incident-Lifecycle: open -> (cooldown-gededupt) -> recovered (wenn Symptom weg) / noted.
"""
import configparser, glob, json, logging, os, shutil, signal, sqlite3, sys, time, uuid
from datetime import datetime, timedelta, timezone

try:
    import psycopg2
except ImportError:  # engine/Incident-Logik bleibt ohne PG testbar
    psycopg2 = None

    class _PGStub:
        class OperationalError(Exception):
            pass
    psycopg2 = _PGStub()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('jarvis-watchdog')
running = True
BASE = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(BASE, 'state')
INCIDENT_DIR = os.path.join(BASE, 'incidents')
os.makedirs(STATE_DIR, exist_ok=True)
os.makedirs(INCIDENT_DIR, exist_ok=True)

# Event-Kinds, die echte Ausführung/Fortschritt belegen (SPEC §7: PROGRESS_EVIDENCE)
EVIDENCE_KINDS = {
    'planned', 'plan', 'claude', 'claude_done', 'cloud', 'cloud_done',
    'step_done', 'step_failed', 'correction', 'recovered', 'deferred', 'question',
}
NON_EVIDENCE_KINDS = {'submitted', 'finished', 'failed', 'cancelled', 'attribution'}
TERMINAL_STATES = {'done', 'partial', 'failed', 'cancelled'}
ACTIVE_STATES = {'queued', 'planning', 'running'}
WAITING_STATES = {'waiting_approval', 'waiting_pc'}


def handle_signal(sig, frame):
    global running
    log.info('Signal %s received, shutting down', sig)
    running = False

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


def load_config(path='/etc/jarvis/watchdog.conf'):
    cfg = configparser.ConfigParser()
    cfg.read(path)
    return cfg


def get_conn(cfg):
    with open(cfg.get('database', 'creds_file')) as f:
        password = f.read().strip()
    return psycopg2.connect(
        dbname=cfg.get('database', 'dbname'), user=cfg.get('database', 'user'),
        host=cfg.get('database', 'host', fallback='127.0.0.1'),
        port=cfg.getint('database', 'port', fallback=5432), password=password)


# ---------------------------------------------------------------- incidents

class IncidentStore:
    """JSONL-Append + offene-Incidents-State mit Dedup/Cooldown/Recovery."""

    def __init__(self):
        self.state_path = os.path.join(STATE_DIR, 'open_incidents.json')
        self.closed_path = os.path.join(STATE_DIR, 'closed_incidents.json')
        self.open = self._load(self.state_path)      # key -> incident dict
        self.closed = self._load(self.closed_path)   # key -> last closed ts

    @staticmethod
    def _load(p):
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self):
        tmp = self.state_path + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(self.open, f)
        os.replace(tmp, self.state_path)
        tmp = self.closed_path + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(self.closed, f)
        os.replace(tmp, self.closed_path)

    @staticmethod
    def key(adapter, subject, classification):
        return f'{adapter}:{subject}:{classification}'

    def open_incident(self, adapter, subject, classification, symptoms, alert_cb, cooldown_min):
        key = self.key(adapter, subject, classification)
        now = time.time()
        if key in self.open:
            return None  # bereits offen
        last_closed = self.closed.get(key, 0)
        if now - last_closed < cooldown_min * 60:
            return None  # Cooldown nach Recovery
        inc = {
            'incident_id': 'i-' + datetime.now(timezone.utc).strftime('%Y%m%d') + '-' + uuid.uuid4().hex[:8],
            'opened_ts': now, 'adapter': adapter, 'subject': subject,
            'classification': classification, 'symptoms': symptoms,
            'state': 'open', 'closed_ts': None, 'close_reason': None,
        }
        self.open[key] = inc
        day = datetime.now(timezone.utc).strftime('%Y%m%d')
        with open(os.path.join(INCIDENT_DIR, f'incidents-{day}.jsonl'), 'a') as f:
            f.write(json.dumps(inc, ensure_ascii=False) + '\n')
        alert_cb(inc)
        self._save()
        return inc

    def reconcile(self, current_keys, now):
        """Issues, die nicht mehr auftreten -> recovered."""
        recovered = []
        for key in list(self.open):
            if key not in current_keys:
                inc = self.open.pop(key)
                inc['state'] = 'recovered'
                inc['closed_ts'] = now
                inc['close_reason'] = 'symptom_gone'
                self.closed[key] = now
                recovered.append(inc)
                day = datetime.now(timezone.utc).strftime('%Y%m%d')
                with open(os.path.join(INCIDENT_DIR, f'incidents-{day}.jsonl'), 'a') as f:
                    f.write(json.dumps(inc, ensure_ascii=False) + '\n')
                log.warning('RECOVERED %s %s (%s)', inc['incident_id'], key, inc['classification'])
        if recovered:
            self._save()


# ---------------------------------------------------------------- engine adapter

def snapshot_db(src, dst_dir):
    """Kopiere DB (+WAL/SHM) in Watchdog-State; Analyse auf der Kopie (read-only, lock-sicher)."""
    base = os.path.basename(src)
    dst = os.path.join(dst_dir, base)
    for suffix in ('', '-wal', '-shm'):
        s = src + suffix
        if os.path.exists(s):
            shutil.copy2(s, dst + suffix)
    return dst


def analyze_engine_jobdb(db_path, cfg):
    findings = []
    now = time.time()
    queued_grace = cfg.getint('engine', 'queued_grace_minutes', fallback=15) * 60
    progress_to = cfg.getint('engine', 'progress_timeout_minutes', fallback=10) * 60
    waiting_to = cfg.getint('engine', 'waiting_timeout_minutes', fallback=240) * 60

    snap = snapshot_db(db_path, STATE_DIR)
    con = sqlite3.connect('file:%s?mode=ro' % snap, uri=True)
    try:
        rows = con.execute(
            "SELECT id, state, created, updated, started, lease_owner, lease_until, tokens_new "
            "FROM jobs WHERE state NOT IN ('done','partial','failed','cancelled')").fetchall()
        for jid, state, created, updated, started, lease_owner, lease_until, tokens_new in rows:
            age = now - updated
            if state == 'queued':
                if now - created > queued_grace:
                    findings.append((jid, 'STALLED_NEVER_STARTED',
                                     {'state': state, 'queued_seconds': int(now - created)}))
            elif state in ('planning', 'running'):
                last_ev = con.execute(
                    "SELECT MAX(ts) FROM job_events WHERE job_id=? AND kind IN (%s)"
                    % ','.join('?' * len(EVIDENCE_KINDS)),
                    (jid, *sorted(EVIDENCE_KINDS))).fetchone()[0]
                last_ev = last_ev or (started or created)
                ev_age = now - last_ev
                if age <= progress_to and ev_age <= progress_to:
                    continue  # frisch -> OK
                symptoms = {'state': state, 'updated_age_s': int(age),
                            'last_evidence_age_s': int(ev_age), 'tokens_new': tokens_new,
                            'lease_owner': lease_owner, 'lease_until': lease_until or 0}
                if lease_owner and lease_until and lease_until > now:
                    findings.append((jid, 'STALLED_ZOMBIE_LEASE', symptoms))
                else:
                    findings.append((jid, 'STALLED_NO_PROGRESS', symptoms))
            elif state in WAITING_STATES:
                if age > waiting_to:
                    findings.append((jid, 'WAITING_TIMEOUT',
                                     {'state': state, 'waiting_seconds': int(age)}))
        active_ids = {r[0] for r in rows}
        return findings, active_ids
    finally:
        con.close()


def engine_scan(cfg):
    findings = []
    active_ids = set()
    patterns = cfg.get('engine', 'db_glob', fallback='/srv/ma-home/library/.jarvis/v16/*/brain.db')
    for db_path in sorted(glob.glob(patterns)):
        f, ids = analyze_engine_jobdb(db_path, cfg)
        findings.extend(f)
        active_ids |= ids
    return findings, active_ids


# ---------------------------------------------------------------- recovery manager (SPEC §9)

class RecoveryManager:
    """Deterministische Recovery-Leiter L1-L5. Fail-closed: Aktionen nur, wo
    ohne Sandbox-Ausweitung sicher; echte Grenzen werden eskaliert statt
    vorgetäuscht. Kein Doppelstart: wartet Lease-Ablauf ab, prüft Tick-Frische."""

    def __init__(self, clock=None):
        self.state_path = os.path.join(STATE_DIR, 'recovery_state.json')
        self.state = IncidentStore._load(self.state_path)  # key -> {first_open, last_action, actions, escalated, dead_lettered}
        self.clock = clock or time.time

    def _save(self):
        tmp = self.state_path + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(self.state, f)
        os.replace(tmp, self.state_path)

    @staticmethod
    def _tick_fresh(cfg, now):
        logf = cfg.get('recovery', 'tick_log', fallback='/home/andrew/.local/state/ma-jarvis/tick.log')
        try:
            return now - os.path.getmtime(logf) < cfg.getint('recovery', 'tick_max_age_s', fallback=180)
        except OSError:
            return False

    def _escalate(self, inc, reason, extra, alert_esc, target):
        alert_esc(inc, reason, extra, target)
        log.warning('RECOVERY-ESCALATE %s %s: %s', inc['incident_id'], inc['subject'], reason)

    def process(self, store, cfg, alert_esc):
        now = self.clock()
        esc_after = cfg.getint('recovery', 'escalate_after_minutes', fallback=180) * 60
        dl_hours = cfg.getint('recovery', 'dead_letter_hours', fallback=24)
        esc_target = cfg.get('recovery', 'escalate_target', fallback='kimi-supervisor')
        changed = False

        for key, inc in list(store.open.items()):
            st = self.state.setdefault(key, {'first_open': inc['opened_ts'], 'last_action': 0,
                                             'actions': 0, 'escalated': False, 'dead_lettered': False})
            age = now - inc['opened_ts']
            adapter, cls = inc['adapter'], inc['classification']
            sym = inc.get('symptoms', {})

            if not st['escalated']:
                if adapter == 'engine':
                    self._engine_case(inc, st, now, cfg, alert_esc, esc_target)
                else:
                    # Council-Tasks: kein deterministischer Eingriff erlaubt (Fremdbesitz) -> nach Frist eskalieren
                    if age > esc_after:
                        self._escalate(inc, 'council_task_stalled_open', {'open_since_s': int(age)}, alert_esc, esc_target)
                        st['escalated'] = True
                        changed = True

            if age > dl_hours * 3600 and not st['dead_lettered']:
                with open(os.path.join(INCIDENT_DIR, 'dead_letter.jsonl'), 'a') as f:
                    f.write(json.dumps({'incident': inc, 'age_s': int(age)}, ensure_ascii=False) + '\n')
                self._escalate(inc, 'dead_letter', {'age_s': int(age)}, alert_esc, esc_target)
                st['dead_lettered'] = True
                st['escalated'] = True
                changed = True

        # aufgeräumte Incidents aus Recovery-State entfernen
        for key in list(self.state):
            if key not in store.open:
                del self.state[key]
                changed = True
        if changed:
            self._save()

    def _engine_case(self, inc, st, now, cfg, alert_esc, esc_target):
        cls = inc['classification']
        sym = inc.get('symptoms', {})
        esc_after = cfg.getint('recovery', 'escalate_after_minutes', fallback=180) * 60
        zombie_margin = cfg.getint('recovery', 'zombie_lease_escalate_margin_s', fallback=3600)
        age = now - inc['opened_ts']

        if cls == 'STALLED_NEVER_STARTED':
            # L1: Engine-Selbstheilung verifizieren (Tick frisch -> Job wird aufgenommen); sonst L2-Diagnose
            if self._tick_fresh(cfg, now):
                if st['actions'] == 0:
                    log.info('RECOVERY L1 %s: tick frisch, warte Engine-Aufnahme', inc['subject'])
                    st['actions'] += 1
            elif age > esc_after and not st['escalated']:
                self._escalate(inc, 'tick_stale_no_intake', {'tick_fresh': False}, alert_esc, esc_target)
                st['escalated'] = True

        elif cls == 'STALLED_ZOMBIE_LEASE':
            # L1: Lease-Ablauf abwarten (kein Doppelstart). Fernzukünftiger Lease -> eskalieren.
            lease_until = sym.get('lease_until', 0)
            if lease_until and lease_until - now > zombie_margin:
                if not st['escalated']:
                    self._escalate(inc, 'zombie_lease_far_future', {'lease_until_in_s': int(lease_until - now)}, alert_esc, esc_target)
                    st['escalated'] = True
            elif st['actions'] == 0:
                log.info('RECOVERY L1 %s: warte Lease-Ablauf (kein Eingriff, kein Doppelstart)', inc['subject'])
                st['actions'] += 1

        elif cls == 'STALLED_NO_PROGRESS':
            if not sym.get('lease_owner'):
                # kein Lease -> Engine korrigiert nicht von selbst; nach kurzer Frist eskalieren
                if age > esc_after and not st['escalated']:
                    self._escalate(inc, 'no_progress_no_lease', {'open_since_s': int(age)}, alert_esc, esc_target)
                    st['escalated'] = True
            elif st['actions'] == 0:
                log.info('RECOVERY L1 %s: Lease aktiv/Abwarten, Engine-recover uebernimmt nach Ablauf', inc['subject'])
                st['actions'] += 1

        elif cls == 'WAITING_TIMEOUT':
            if not st['escalated']:
                self._escalate(inc, 'waiting_owner_decision', {'state': sym.get('state')}, alert_esc, esc_target)
                st['escalated'] = True


# ---------------------------------------------------------------- L3 service recovery (Recovery-Leiter Stufe 3)
# Defekten Dienst mit Leitplanken neu starten: erst nach anhaltendem Ausfall
# (grace), max. max_restarts je window_s, Meldung bei erschoepftem Budget,
# Zaehler-Reset bei Erholung. Kein LLM. Restart nur via sudoers-Whitelist.
L3_SERVICES = {'ma-claude-bridge': 'ma-claude-bridge.service', 'ma-home-web': 'ma-home-web.service'}


def services_scan(state, run=None, now=None, push_event=None, down_for_s=60, max_restarts=3, window_s=3600):
    import subprocess as _sp
    if run is None:
        run = lambda argv, **kw: _sp.run(argv, capture_output=True)
    push_event = push_event or (lambda e: None)
    now = now if now is not None else time.time()
    for svc, unit in L3_SERVICES.items():
        st = state.setdefault(svc, {'down_since': None, 'restarts': [], 'exhausted': False})
        rc = run(['systemctl', 'is-active', unit]).returncode
        if rc == 0:
            if st['down_since'] is not None or st['exhausted']:
                push_event({'event': 'service_recovered', 'service': svc, 'unit': unit})
            st['down_since'] = None
            st['exhausted'] = False
            continue
        if st['down_since'] is None:
            st['down_since'] = now
            continue
        st['restarts'] = [r for r in st['restarts'] if now - r[0] < window_s]
        if now - st['down_since'] < down_for_s:
            continue
        if len(st['restarts']) < max_restarts:
            cmd = ['sudo', '-n', 'systemctl', 'restart', unit]
            run(cmd)
            st['restarts'].append((now, ' '.join(cmd)))
            log.warning('RECOVERY L3 %s: %s neu gestartet (%d/%d im Fenster)', svc, unit,
                        len(st['restarts']), max_restarts)
            push_event({'event': 'restarted', 'service': svc, 'unit': unit, 'attempt': len(st['restarts'])})
        elif not st['exhausted']:
            st['exhausted'] = True
            log.error('RECOVERY L3 %s: Neustart-Budget erschoepft (%d/%d) - eskaliere', svc,
                      len(st['restarts']), max_restarts)
            push_event({'event': 'restart_budget_exhausted', 'service': svc, 'unit': unit,
                        'restarts_in_window': len(st['restarts'])})


# ---------------------------------------------------------------- council adapter

def council_scan(conn, cfg, alert_cb):
    findings = []
    stale_min = cfg.getint('watchdog', 'heartbeat_stale_minutes', fallback=5)
    stalled_min = cfg.getint('watchdog', 'task_stalled_minutes', fallback=30)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_min)
    with conn.cursor() as cur:
        cur.execute("SELECT agent_handle, last_heartbeat FROM heartbeats WHERE last_heartbeat < %s AND agent_handle != 'watchdog'", (cutoff,))
        for agent, last_hb in cur.fetchall():
            findings.append((agent, 'STALE_AGENT', {'last_heartbeat': str(last_hb)}))
        cutoff2 = datetime.now(timezone.utc) - timedelta(minutes=stalled_min)
        cur.execute("SELECT task_id, title, updated_at FROM tasks WHERE status = 'ACTIVE' AND updated_at < %s", (cutoff2,))
        for tid, title, updated in cur.fetchall():
            # Negative Probe (SPEC §18): Nachrichten-Aussagen zählen nicht -
            # nur updated_at/heartbeats belegen Fortschritt.
            findings.append((tid, 'STALLED_TASK', {'title': title, 'updated_at': str(updated)}))
    return findings


# ---------------------------------------------------------------- main loop

def make_alerter(conn, cfg):
    channel = cfg.get('watchdog', 'alert_channel', fallback='system-alerts')
    target = cfg.get('watchdog', 'alert_target', fallback='jarvis-cloud-dev')

    def alert(inc):
        log.warning('INCIDENT %s %s %s %s', inc['incident_id'], inc['adapter'], inc['subject'], inc['classification'])
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO messages (message_id, from_agent, to_agent, channel, content, created_at) "
                "VALUES (gen_random_uuid()::text, 'watchdog', %s, %s, %s::jsonb, NOW())",
                (target, channel, json.dumps({
                    'type': 'WATCHDOG_INCIDENT',
                    'incident_id': inc['incident_id'],
                    'adapter': inc['adapter'],
                    'subject': inc['subject'],
                    'classification': inc['classification'],
                    'symptoms': inc['symptoms'],
                }, ensure_ascii=False)))
        conn.commit()
    return alert


def write_self_heartbeat(conn, handle):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO heartbeats (agent_handle, last_heartbeat, status) VALUES (%s, NOW(), 'ACTIVE') "
            "ON CONFLICT (agent_handle) DO UPDATE SET last_heartbeat=NOW(), status='ACTIVE'", (handle,))
    conn.commit()


def main():
    cfg = load_config()
    interval = cfg.getint('watchdog', 'interval_seconds', fallback=30)
    eval_every = max(1, cfg.getint('watchdog', 'progress_eval_every_ticks', fallback=2))
    cooldown = cfg.getint('watchdog', 'incident_cooldown_minutes', fallback=30)
    self_handle = cfg.get('watchdog', 'self_handle', fallback='watchdog')
    log.info('Evidence-Watchdog starting: interval=%ds eval_every=%d cooldown=%dmin MONITOR_ONLY=hermes,cloud-dev',
             interval, eval_every, cooldown)
    store = IncidentStore()
    recovery = RecoveryManager()
    l3_state = {}
    tick_no = 0
    conn = None
    while running:
        tick_no += 1
        try:
            if conn is None or conn.closed:
                conn = get_conn(cfg)
            alert = make_alerter(conn, cfg)
            write_self_heartbeat(conn, self_handle)

            if tick_no % eval_every == 1 or eval_every == 1:
                current_keys = set()
                # engine
                try:
                    findings, _active = engine_scan(cfg)
                    for jid, cls, symptoms in findings:
                        current_keys.add(IncidentStore.key('engine', jid, cls))
                        store.open_incident('engine', jid, cls, symptoms, alert, cooldown)
                except Exception as e:
                    log.error('engine adapter failed: %s', e)
                # council
                try:
                    findings = council_scan(conn, cfg, alert)
                    for subj, cls, symptoms in findings:
                        current_keys.add(IncidentStore.key('council', subj, cls))
                        store.open_incident('council', subj, cls, symptoms, alert, cooldown)
                except Exception as e:
                    log.error('council adapter failed: %s', e)

                # recovery leiter (SPEC §9): L1 verifizieren/warten, L5 eskalieren, dead letters
                try:
                    def alert_esc(inc, reason, extra, target):
                        log.warning('ESCALATION %s %s: %s', inc['incident_id'], inc['subject'], reason)
                        with conn.cursor() as cur:
                            cur.execute(
                                "INSERT INTO messages (message_id, from_agent, to_agent, channel, content, created_at) "
                                "VALUES (gen_random_uuid()::text, 'watchdog', %s, %s, %s::jsonb, NOW())",
                                (target, cfg.get('watchdog', 'alert_channel', fallback='system-alerts'),
                                 json.dumps({'type': 'RECOVERY_ESCALATION', 'incident_id': inc['incident_id'],
                                             'adapter': inc['adapter'], 'subject': inc['subject'],
                                             'classification': inc['classification'], 'reason': reason,
                                             'extra': extra}, ensure_ascii=False)))
                        conn.commit()
                    recovery.process(store, cfg, alert_esc)
                except Exception as e:
                    log.error('recovery manager failed: %s', e)

                # L3: Dienst-Neustart mit Leitplanken (bridge, portal)
                try:
                    l3_events = []
                    services_scan(l3_state, push_event=l3_events.append)
                    for ev in l3_events:
                        current_keys.add(IncidentStore.key('services', ev['service'], ev['event']))
                        store.open_incident('services', ev['service'], ev['event'],
                                            {'unit': ev['unit']}, alert, cooldown)
                except Exception as e:
                    log.error('services L3 failed: %s', e)

                store.reconcile(current_keys, time.time())
                if not current_keys:
                    log.info('eval OK - no open issues')
        except psycopg2.OperationalError as e:
            log.error('PG connection lost: %s - reconnecting next tick', e)
            try:
                conn.close()
            except Exception:
                pass
            conn = None
        except Exception as e:
            log.error('tick failed: %s', e)
        time.sleep(interval)
    log.info('Watchdog stopped')


if __name__ == '__main__':
    main()
