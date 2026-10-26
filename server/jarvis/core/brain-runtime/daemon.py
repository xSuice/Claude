#!/usr/bin/env python3
"""V10 event-driven supervisor: the brain's continuous, mostly local operation.

Each tick (default 60 s), bounded and logged:
  1 self-check   heartbeat; a gap longer than 3 ticks is reported (outage detection)
  2 homeostasis  load, memory, disk -> 'conserve' mode: fewer steps, no sleep/research
  3 perception   sensors on their own interval (slower in conserve mode)
  4 attention    every NEW deviation is answered once:
                   known (confirmed procedure) -> procedure goal, runs locally, no Claude
                   unknown + severe + Claude route enabled -> one budgeted diagnosis job
                   otherwise -> notice for a human
  5 action       executive.run_once (verified by independent checks, resumable)
  6 learning     closed goals -> procedure stats / new *proposed* procedures;
                 finished Claude jobs -> unconfirmed memory proposals (never facts)
  7 sleep        once a day at the quiet hour: vault index, consolidation, failure
                 suggestions, optional research for the top weakness, metrics rollup, pruning
Never: unbounded loops, model calls outside the existing queue, changes to its own limits.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from brain_core import Brain  # noqa: E402
from cognitive_loop import CognitiveLoop  # noqa: E402
from executive import Executive  # noqa: E402
from procedures import Procedures  # noqa: E402
import runner  # noqa: E402
import selfmodel  # noqa: E402
import sensors as senses  # noqa: E402

SCHEMA = '''
CREATE TABLE IF NOT EXISTS daemon_state(
    owner TEXT PRIMARY KEY, started INTEGER, last_tick INTEGER, ticks INTEGER NOT NULL DEFAULT 0,
    errors INTEGER NOT NULL DEFAULT 0, last_error TEXT, mode TEXT, last_sensor INTEGER,
    last_sleep_day TEXT, last_anomaly_seen INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS notices(
    id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL, created INTEGER NOT NULL,
    level TEXT NOT NULL CHECK(level IN ('info','warning','action')), text TEXT NOT NULL,
    read INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS harvested_jobs(job_id TEXT PRIMARY KEY, owner TEXT NOT NULL, created INTEGER NOT NULL);
'''
DEFAULTS = {'tick_seconds': 60, 'sensor_interval_seconds': 300, 'sleep_hour': 3, 'timezone': None,
            'diagnosis': None, 'research': {'enabled': False, 'min_failures': 3}, 'homeostasis': {},
            'retention_days': 90, 'max_notices_per_tick': 10}


class Daemon:
    def __init__(self, brain: Brain, project: str, executive: Executive, *, sensors_cfg=None,
                 autonomy_cfg=None, opts=None, sensor_runner=None, vault=None, perf=None):
        self.brain, self.project = brain, brain._project(project)
        self.loop, self.ex = CognitiveLoop(brain), executive
        self.proc = Procedures(brain)
        self.sensors_cfg = senses.validate(sensors_cfg) if sensors_cfg else None
        self.autonomy = autonomy_cfg
        self.o = {**DEFAULTS, **(opts or {})}
        diag = self.o['diagnosis']
        if diag and (diag.get('action') not in executive.actions or diag.get('check') not in executive.actions):
            raise ValueError('diagnosis action/check must be allowlisted')
        self.sensor_runner = sensor_runner or senses._run
        self.vault = vault
        self.perf = perf  # V11: PerfIntel or None
        self.autopilot = None  # V11: perf_autopilot.Autopilot, attached by build() when pinned allowlist is valid
        self._first = True
        with brain.connection(True) as db:
            db.executescript(SCHEMA)
            db.execute('INSERT OR IGNORE INTO daemon_state(owner,started) VALUES(?,?)', (brain.identity, int(time.time())))

    # ---------- helpers ----------
    def _state(self):
        with self.brain.connection() as db:
            return dict(db.execute('SELECT * FROM daemon_state WHERE owner=?', (self.brain.identity,)).fetchone())

    def _save(self, **kw):
        with self.brain.connection(True) as db:
            db.execute('UPDATE daemon_state SET ' + ','.join(f'{k}=?' for k in kw) + ' WHERE owner=?',
                       (*kw.values(), self.brain.identity))

    def notice(self, level, text, now=None):
        with self.brain.connection(True) as db:
            db.execute('INSERT INTO notices(owner,created,level,text) VALUES(?,?,?,?)',
                       (self.brain.identity, now or int(time.time()), level, runner.redact(text)[:500]))

    def _local(self, now):
        if self.o['timezone']:
            from zoneinfo import ZoneInfo
            return datetime.fromtimestamp(now, ZoneInfo(self.o['timezone']))
        return datetime.fromtimestamp(now)

    # ---------- attention: new deviations ----------
    def _new_anomalies(self, since):
        with self.brain.connection() as db:
            return [dict(r) for r in db.execute(
                "SELECT a.rowid rid,a.id,a.created,e.subject,v.value,v.severity FROM cognitive_anomalies a "
                "JOIN cognitive_events v ON v.id=a.event_id JOIN cognitive_expectations e ON e.id=a.expectation_id "
                "WHERE a.owner=? AND a.project=? AND a.status='open' AND e.active=1 AND a.rowid>? "
                "ORDER BY v.severity DESC, a.rowid ASC LIMIT 20", (self.brain.identity, self.project, since))]

    def _unhandled_known(self, cursor):
        """Older open deviations without any goal, re-checked only for a now-confirmed procedure."""
        with self.brain.connection() as db:
            rows = [dict(r) for r in db.execute(
                "SELECT a.rowid rid,a.id,a.created,e.subject,v.value,v.severity FROM cognitive_anomalies a "
                "JOIN cognitive_events v ON v.id=a.event_id JOIN cognitive_expectations e ON e.id=a.expectation_id "
                "WHERE a.owner=? AND a.project=? AND a.status='open' AND e.active=1 AND a.rowid<=? AND NOT EXISTS "
                "(SELECT 1 FROM goal_links l WHERE l.anomaly_id=a.id) ORDER BY v.severity DESC LIMIT 20",
                (self.brain.identity, self.project, cursor))]
        return [r for r in rows if self.proc.match(self.project, r['subject'], r['value'])]

    def attend(self, now) -> list[dict]:
        st, out = self._state(), []
        new = self._new_anomalies(st['last_anomaly_seen'])
        for a in (self._unhandled_known(st['last_anomaly_seen']) + new)[:self.o['max_notices_per_tick']]:
            subj, val = a['subject'], a['value']
            if self.proc.open_goal_for(self.project, subj):
                out.append({'subject': subj, 'decision': 'already handled'}); continue
            known = self.proc.match(self.project, subj, val)
            if known:
                try:
                    r = self.proc.instantiate(self.ex, known[0], a['id'], subj, val, idem_key=f"anomaly:{a['id']}")
                    self.notice('info', f"Bekannte Abweichung {subj}={val}: Ablauf #{known[0]['id']} gestartet", now)
                    out.append({'subject': subj, 'decision': 'procedure', **r}); continue
                except ValueError as e:
                    self.notice('warning', f'Ablauf #{known[0]["id"]} nicht ausführbar: {e}', now)
            diag = self.o['diagnosis']
            route_ok = (self.autonomy and self.autonomy.get('enabled')) or 'helper_task' in self.ex.actions.get((diag or {}).get('action'), {})
            if diag and a['severity'] >= diag.get('min_severity', 4) and route_ok:
                packet = self.write_packet(a, now)
                helper = 'helper_task' in self.ex.actions.get(diag['action'], {})
                sens = next((s for s in (self.sensors_cfg or {}).get('sensors', []) if f"sensor:{s['id']}" == subj), {})
                g = self.ex.orders.open(self.project, f'Diagnose {subj}={val}'[:160], f'Ursache für {subj} benannt',
                                        [f'Read-only-Diagnose von {subj} (beobachtet: {val}); Paket {packet}'],
                                        priority=2, idem_key=f"diagnosis:{a['id']}", risk='read', claude_budget=1,
                                        quality='root cause with evidence lines; no changes made', topic=packet,
                                        helper_budget=max(0, min(3, int(diag.get('helper_budget', 1)))) if helper else 0, data_class=sens.get('data_class', 'internal'))
                if g['duplicate']:
                    out.append({'subject': subj, 'decision': 'already handled'}); continue
                with self.brain.connection() as db:
                    sid = db.execute('SELECT id FROM steps WHERE goal_id=?', (g['goal_id'],)).fetchone()[0]
                self.ex.bind(self.project, sid, diag['action'], diag['check'], by='admin')  # operator-configured
                self.proc.link(g['goal_id'], a['id'], subj, val, 'diagnosis')
                self.notice('info', f'Unbekannte Abweichung {subj}={val} (Schwere {a["severity"]}): Diagnose eingeplant', now)
                out.append({'subject': subj, 'decision': 'diagnosis', 'goal_id': g['goal_id']})
            else:
                self.notice('action', f'Unbekannte Abweichung {subj}={val} (Schwere {a["severity"]}): '
                                      'kein bestätigter Ablauf - bitte prüfen', now)
                out.append({'subject': subj, 'decision': 'human'})
        if new:
            self._save(last_anomaly_seen=max(a['rid'] for a in new))  # rowid cursor: no same-second gaps
        return out

    # ---------- V10.1: diagnosis packet (local pre-analysis, so Claude reads little) ----------
    def write_packet(self, a, now) -> str:
        from logdigest import digest
        subj, sid = a['subject'], a['subject'].split(':', 1)[-1]
        sensor = next((s for s in (self.sensors_cfg or {}).get('sensors', []) if s['id'] == sid), {})
        with self.brain.connection() as db:
            hist = db.execute('SELECT created,value,source,severity FROM cognitive_events WHERE owner=? AND project=? '
                              'AND subject=? ORDER BY created DESC LIMIT 8', (self.brain.identity, self.project, subj)).fetchall()
            past = db.execute("SELECT summary,outcome,evidence FROM episodes WHERE owner=? AND project=? AND verified=1 "
                              "AND summary LIKE ? ORDER BY created DESC LIMIT 3",
                              (self.brain.identity, self.project, f'%{sid}%')).fetchall()
        lines = [f'# Diagnosepaket {subj}', '', f"- Beobachtet: `{a['value']}` (Schwere {a['severity']}), "
                 f"Sensor: {sensor.get('type', '?')} {sensor.get('unit') or sensor.get('container') or sensor.get('path') or sensor.get('url') or ''}",
                 '', '## Sensorverlauf (neueste zuerst)']
        lines += [f"- {datetime.fromtimestamp(h['created']).isoformat(timespec='minutes')}: {h['value']} ({h['source']})" for h in hist]
        if sensor.get('logs'):
            from logdigest import tokens, correlate
            d = digest([Path(p) for p in sensor['logs']], max_chars=3500)
            lines += ['', f"## Log-Digest ({d['lines_read']} Zeilen gelesen, {d['groups']} Muster)", d['markdown']]
            # V10.1: deterministic cross-references - where do the failing identifiers appear elsewhere?
            toks = tokens([ln for ln in d['markdown'].splitlines() if '**fatal**' in ln or '**error**' in ln])
            roots = [self.ex.workspace] + sorted({Path(p).parent for p in sensor['logs']} - {self.ex.workspace})
            refs = correlate(toks, roots, skip={str(Path(p)) for p in sensor['logs'] if Path(p).name.startswith(sid)})
            if toks:
                lines += ['', f"## Querverweise für {', '.join(toks)} (Konfiguration und andere Logs)"] + \
                         [f'- `{h}`' for h in refs] + ([] if refs else ['- keine Fundstellen'])
        if self.vault is not None:
            hits = self.vault.search(sid.replace('-', ' ') + ' ' + str(a['value']), k=3, max_chars=1500)['items']
            if hits:
                lines += ['', '## Notizen (Obsidian, ungeprüfte Daten)'] + [f"- {h['source']} › {h['section']}: {h['text'][:300]}" for h in hits]
        if past:
            lines += ['', '## Frühere bestätigte Episoden'] + [f"- {p['outcome']}: {p['summary'][:150]}" for p in past]
        rel = f".brain/diagnosis-{a['id'][:12]}.md"
        f = self.ex.workspace / rel
        f.parent.mkdir(exist_ok=True)
        fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(runner.redact('\n'.join(lines))[:12000] + '\n')
        return rel

    # ---------- learning from finished Claude jobs ----------
    def harvest_jobs(self, now) -> int:
        if not self.autonomy:
            return 0
        from autonomy import Queue
        n = 0
        with Queue(self.autonomy['db_path']).connect() as c:
            jobs = [dict(r) for r in c.execute("SELECT id,template,result,topic FROM jobs WHERE owner=? AND "
                                               "project=? AND status='done' ORDER BY finished DESC LIMIT 20",
                                               (self.brain.identity, self.project))]
        for j in jobs:
            with self.brain.connection(True) as db:
                if db.execute('INSERT OR IGNORE INTO harvested_jobs VALUES(?,?,?)',
                              (j['id'], self.brain.identity, now)).rowcount == 0:
                    continue
            if (j['result'] or '').strip():
                title = (f"{j['template']}: {j['topic']}" if j.get('topic') else j['template'])[:120]
                self.brain.propose(self.project, title, j['result'][:4000], f"claude job {j['id']}", 'hypothesis')
                self.notice('info', f'Ergebnis von {title} liegt als unbestätigter Vorschlag vor', now)
                n += 1
        return n

    # ---------- sleep / consolidation ----------
    def sleep(self, now) -> dict:
        out = {}
        if self.vault is not None:
            out['vault'] = self.vault.build()
        out['consolidation'] = self.loop.consolidate(self.project)
        sugg = self.brain.tick(self.project)['new_suggestions']
        for s in sugg:
            self.notice('action', f"Wiederkehrender bestätigter Fehler ({s['cause']}): Verbesserung prüfen", now)
        out['suggestions'] = len(sugg)
        r = self.o['research']
        if r.get('enabled') and self.autonomy and self.autonomy.get('enabled') \
                and 'extension_research' in self.autonomy['allowed_templates']:
            weak = selfmodel.snapshot(self.brain, self.project, self.ex, self.proc)['weaknesses']
            top = [w for w in weak['recurring_verified_failures_30d'] if w['failures'] >= r.get('min_failures', 3)]
            if top:
                from autonomy import Queue
                topic = top[0]['task_type'].replace('action:', 'failing action ')[:80]
                try:
                    Queue(self.autonomy['db_path']).enqueue(self.autonomy, self.brain.identity, self.project,
                                                            'extension_research', str(self.ex.workspace), topic=topic)
                    out['research_queued'] = topic
                except (ValueError, PermissionError) as e:
                    out['research_skipped'] = str(e)
        if self.perf is not None:
            out['perf_retention'] = self.perf.downsample(now)
            fc = self.perf.disk_forecast(now)
            if fc and fc.get('days_to_floor') is not None and fc['days_to_floor'] < 14:
                self.notice('action', f"Frühwarnung: Platte in ~{fc['days_to_floor']} Tagen unter 5 % frei "
                                      f"(Trend {fc['trend_pct_per_day']} %/Tag)", now)
            out['disk_forecast'] = fc
        yesterday = (self._local(now) - timedelta(days=1)).date()
        out['metrics'] = selfmodel.rollup(self.brain, yesterday)
        cutoff = now - self.o['retention_days'] * 86400
        with self.brain.connection(True) as db:
            out['pruned_runs'] = db.execute('DELETE FROM exec_runs WHERE owner=? AND started<?',
                                            (self.brain.identity, cutoff)).rowcount
            db.execute('DELETE FROM notices WHERE owner=? AND read=1 AND created<?', (self.brain.identity, cutoff))
        return out

    # ---------- one tick ----------
    def tick(self, now: int | None = None) -> dict:
        now = int(time.time()) if now is None else now
        st, rep = self._state(), {'time': now}
        if self._first and st['last_tick'] and now - st['last_tick'] > 3 * self.o['tick_seconds']:
            self.notice('warning', f"Daemon war {(now - st['last_tick']) // 60} min nicht aktiv - Arbeit wird fortgesetzt", now)
            rep['outage_s'] = now - st['last_tick']
        self._first = False
        from orders import killed
        if killed(self.brain):  # V10.1 kill switch: heartbeat only, no perception-triggered work, no actions
            if st['mode'] != 'killed':
                self.notice('warning', 'Not-Aus aktiv (Datei KILL): keine Aktionen bis zur Entfernung', now)
            self._save(last_tick=now, ticks=st['ticks'] + 1, mode='killed')
            return {**rep, 'killed': True}
        h = selfmodel.homeostasis(self.brain.db_path.parent, self.o['homeostasis'])
        if self.perf is not None and self.perf.due(now):  # V11: measured, learned, hysteresis-protected state
            ps = self.perf.sample(now)
            rep['perf'] = {'mode': ps['mode'], 'changes': ps['changes'], 'interval': ps['interval']}
            for ch in ps['changes']:
                if ch['kind'] == 'enter':
                    self.notice('warning', f"Engpass {ch['cond']}: {ch['evidence']}", now)
            if self.perf.last is not None and self._local(now).hour != self._local(st['last_tick'] or now).hour:
                self.perf.downsample(now)
        if self.perf is not None:
            pm = self.perf.mode()
            if pm != 'normal':
                h = {**h, 'mode': pm, 'reasons': h['reasons'] + [c for c in self.perf.active() if c != 'self_load']}
        rep['mode'] = h['mode']
        if h['mode'] in ('conserve', 'protect') and st['mode'] != h['mode']:
            self.notice('warning', f"Ressourcen knapp ({', '.join(h['reasons'])}): "
                                   f"{'Schutzmodus - keine neuen Aktionen' if h['mode'] == 'protect' else 'Sparbetrieb'}", now)
        if self.loop.health(self.project)['paused']:
            self._save(last_tick=now, ticks=st['ticks'] + 1, mode='paused')
            return {**rep, 'paused': True}
        interval = self.o['sensor_interval_seconds'] * (3 if h['mode'] in ('conserve', 'protect') else 1)
        if self.sensors_cfg and now - (st['last_sensor'] or 0) >= interval:
            s = senses.scan(self.loop, self.sensors_cfg, self.sensor_runner)
            rep['sensors'] = {'observed': s.get('observed'), 'deviations': s.get('deviations')}
            self._save(last_sensor=now)
        rep['attention'] = self.attend(now)
        saved = self.ex.limits['max_steps_per_run']
        if h['mode'] in ('conserve', 'protect'):
            self.ex.limits['max_steps_per_run'] = 1 if h['mode'] == 'conserve' else 0
        self.ex.defer_remote = h['mode'] != 'normal' or bool(self.o.get('defer_remote_override'))  # V11
        try:
            ex = self.ex.run_once(self.project, now)
        finally:
            self.ex.limits['max_steps_per_run'] = saved
            self.ex.defer_remote = False
        rep['executed'] = [(x['step_id'][:8], x.get('state')) for x in ex.get('executed', [])]
        rep['reconciled'] = len(ex.get('reconciled', []))
        learned = self.proc.review_closed_goals()
        for l in learned['learned']:
            self.notice('action', f"Neuer Ablauf #{l['procedure']} für {l['trigger']} gelernt - "
                                  f"bitte prüfen und mit 'procedures.py confirm {l['procedure']}' bestätigen", now)
        for u in learned['updated']:
            if u['outcome'] == 'failure':
                self.notice('warning', f"Ablauf #{u['procedure']} hat diesmal nicht geholfen", now)
        rep['learning'] = learned
        rep['harvested'] = self.harvest_jobs(now)
        if self.autopilot is not None:
            try:
                rep['autopilot'] = self.autopilot.step(now)
            except Exception as e:  # noqa: BLE001 - the autopilot must never take the daemon down
                rep['autopilot'] = {'state': 'error', 'error': type(e).__name__}
        local = self._local(now)
        if local.hour == self.o['sleep_hour'] and st['last_sleep_day'] != local.date().isoformat() \
                and h['mode'] == 'normal':
            rep['sleep'] = self.sleep(now)
            self._save(last_sleep_day=local.date().isoformat())
        self._save(last_tick=now, ticks=st['ticks'] + 1, mode=h['mode'])
        rep['claude_calls_started'] = 0
        return rep

    def notices(self, unread_only=True, mark_read=False, limit=20) -> list[dict]:
        with self.brain.connection(True) as db:
            rows = [dict(r) for r in db.execute(
                'SELECT id,created,level,text FROM notices WHERE owner=?' + (' AND read=0' if unread_only else '') +
                ' ORDER BY id DESC LIMIT ?', (self.brain.identity, limit))]
            if mark_read and rows:
                db.execute(f"UPDATE notices SET read=1 WHERE owner=? AND id IN ({','.join('?' * len(rows))})",
                           (self.brain.identity, *[r['id'] for r in rows]))
        return rows


STOP = False


def _stop(*_):
    global STOP
    STOP = True


def build(cfg_path: Path) -> Daemon:
    """daemon.json: {"brain_config", "actions", "workspace", "project", optional "sensors",
    "autonomy_config", "vault": true, and any DEFAULTS key}."""
    cfg_path = cfg_path.expanduser().resolve(strict=True)
    d = json.loads(cfg_path.read_text(encoding='utf-8'))
    rel = lambda k: (cfg_path.parent / d[k]).resolve() if not Path(d[k]).is_absolute() else Path(d[k])  # noqa: E731
    bconf_path = rel('brain_config')
    bconf = json.loads(bconf_path.read_text(encoding='utf-8'))
    db = Path(bconf['state_db']).expanduser()
    if not db.is_absolute(): db = (bconf_path.parent / db).resolve()
    brain = Brain(db, bconf['identity'], set(bconf['allowed_projects']))
    auto = None
    if d.get('autonomy_config'):
        from autonomy import load_config
        auto = load_config(rel('autonomy_config'))
    helpers = route = None
    if d.get('providers'):  # V11: optional cloud helpers, default cloud_enabled=false
        from provider_adapter import HelperClient, load as load_providers
        from route_policy import RoutePolicy
        # AP-4: load provider registry (fail-closed, log if unavailable)
        _registry = None
        try:
            from provider_registry import ProviderRegistry
            _registry = ProviderRegistry()
        except Exception as _e:
            import logging
            logging.getLogger("daemon").warning("provider_registry unavailable: %s", _e)
        helpers = HelperClient(load_providers(rel('providers')), brain.db_path.parent / 'helpers.sqlite3', brain.identity)
        r = d.get('router', {})
        route = RoutePolicy(brain.db_path.parent / 'route.sqlite3', r.get('cmd'), helpers, r.get('mode', 'shadow'),
                            r.get('min_success', 0.8), r.get('min_samples', 10), r.get('provider_order', []))
    ex = Executive(brain, runner.load_actions(rel('actions')), rel('workspace'), auto, helpers=helpers, route=route)
    vault = None
    if d.get('vault') and bconf.get('vault'):
        from knowledge_index import VaultIndex
        vault = VaultIndex(Path(bconf['vault_index']), Path(bconf['vault']), bconf.get('vault_roots'),
                           bconf.get('vault_exclude'), bconf.get('timezone'))
    opts = {k: d[k] for k in DEFAULTS if k in d}
    perf = None
    if d.get('performance', {}).get('enabled', True):
        from performance_intelligence import PerfIntel, Collector
        p = d.get('performance', {})
        perf = PerfIntel(brain.db_path.parent / 'perf.sqlite3', Collector(disk_paths=p.get('disk_paths', ['/'])),
                         p.get('limits'), p.get('min_interval', 60), p.get('max_interval', 300))
    dmn = Daemon(brain, d['project'], ex, sensors_cfg=senses.load(rel('sensors')) if d.get('sensors') else None,
                 autonomy_cfg=auto, opts=opts, vault=vault, perf=perf)
    ap = d.get('autopilot')
    if ap and ap.get('allowlist'):
        from perf_autopilot import Autopilot, load_allowlist
        try:
            dmn.autopilot = Autopilot(dmn, load_allowlist(rel_path(cfg_path, ap['allowlist']), ap.get('sha256', '')),
                                      autorun=ap.get('autorun', False))
        except (OSError, ValueError, PermissionError) as e:
            dmn.notice('warning', f'Autopilot deaktiviert: {e}')
    return dmn


def rel_path(cfg_path, p):
    p = Path(p).expanduser()
    return p if p.is_absolute() else (cfg_path.parent / p).resolve()


UNIT = """[Unit]
Description=MA-Home Cognitive Brain daemon ({ident})
After=network-online.target

[Service]
Type=simple
ExecStart={py} {script} --config {cfg} run
Restart=on-failure
RestartSec=30
Nice=10
MemoryHigh=384M
MemoryMax=512M
CPUQuota=50%
CPUWeight=20
IOWeight=20
IOSchedulingClass=best-effort
IOSchedulingPriority=7
TasksMax=128
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full
UMask=0077

[Install]
WantedBy=default.target
"""


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--config', type=Path, required=True, help='daemon.json')
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('run'); sub.add_parser('once'); sub.add_parser('unit')
    n = sub.add_parser('notices'); n.add_argument('--all', action='store_true'); n.add_argument('--mark-read', action='store_true')
    sub.add_parser('self'); sub.add_parser('doctor')
    au = sub.add_parser('audit'); au.add_argument('--hours', type=int, default=24)
    sub.add_parser('kill'); sub.add_parser('unkill')
    m = sub.add_parser('metrics'); m.add_argument('--days', type=int, default=30)
    sub.add_parser('perf')  # V11: performance report (measured, no model call)
    ap = sub.add_parser('autopilot'); ap.add_argument('action', choices=['list', 'approve']); ap.add_argument('id', nargs='?', type=int)
    hp = sub.add_parser('helpers'); hp.add_argument('--days', type=int, default=30)
    cn = sub.add_parser('canary'); cn.add_argument('--provider', required=True); cn.add_argument('--suite', type=Path, required=True)
    sb = sub.add_parser('scoreboard'); sb.add_argument('--days', type=int, default=7)  # V11.1: results per resource
    a = p.parse_args()
    os.umask(0o077)  # V10.1: every file the daemon creates is owner-only
    if a.cmd == 'unit':
        print(UNIT.format(ident=a.config.stem, py=sys.executable, script=Path(__file__).resolve(),
                          cfg=a.config.expanduser().resolve())); return 0
    try:
        dmn = build(a.config)
    except (OSError, ValueError, KeyError, PermissionError) as e:
        print(f'ERROR: {type(e).__name__}: {e}', file=sys.stderr); return 2
    if a.cmd == 'once':
        print(json.dumps(dmn.tick(), ensure_ascii=False, indent=1)); return 0
    if a.cmd == 'notices':
        print(json.dumps(dmn.notices(not a.all, a.mark_read), ensure_ascii=False, indent=1)); return 0
    if a.cmd == 'self':
        print(json.dumps(selfmodel.snapshot(dmn.brain, dmn.project, dmn.ex, dmn.proc, dmn.sensors_cfg, dmn.autonomy,
                                            dmn.o['homeostasis']), ensure_ascii=False, indent=1)); return 0
    if a.cmd == 'doctor':
        r = selfmodel.doctor(dmn.brain, [a.config]); print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if r['ok'] else 1
    if a.cmd in ('kill', 'unkill'):
        k = dmn.brain.db_path.parent / 'KILL'
        k.touch() if a.cmd == 'kill' else k.unlink(missing_ok=True)
        print(json.dumps({'kill_switch': k.exists()})); return 0
    if a.cmd == 'audit':
        since = int(time.time()) - a.hours * 3600
        with dmn.brain.connection() as db:
            ev = [('run', r[0], f'{r[1]} {r[2]} exit={r[3]}') for r in db.execute(
                'SELECT started,kind,action,exit FROM exec_runs WHERE owner=? AND started>=?', (dmn.brain.identity, since))]
            ev += [('notice', r[0], f'{r[1]}: {r[2]}') for r in db.execute(
                'SELECT created,level,text FROM notices WHERE owner=? AND created>=?', (dmn.brain.identity, since))]
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='improvement_journal'").fetchone():
                ev += [('improve', r[0], f'trial {r[1]}: {r[2]}') for r in db.execute(
                    'SELECT at,trial,step FROM improvement_journal WHERE at>=?', (since,))]
        print(json.dumps([{'kind': k, 'at': datetime.fromtimestamp(t).isoformat(timespec='seconds'), 'what': w}
                          for k, t, w in sorted(ev, key=lambda x: x[1])], ensure_ascii=False, indent=1)); return 0
    if a.cmd == 'metrics':
        print(json.dumps(selfmodel.history(dmn.brain, a.days), ensure_ascii=False, indent=1)); return 0
    if a.cmd == 'perf':
        if not dmn.perf:
            print('{"performance": "disabled"}'); return 1
        print(json.dumps(dmn.perf.report(), ensure_ascii=False, indent=1)); return 0
    if a.cmd == 'autopilot':
        if not dmn.autopilot:
            print('{"autopilot": "not configured"}'); return 1
        if a.action == 'approve':
            if a.id is None:
                print('ERROR: approve needs ID', file=sys.stderr); return 2
            print(json.dumps(dmn.autopilot.approve(a.id), ensure_ascii=False)); return 0
        print(json.dumps(dmn.autopilot.history(), ensure_ascii=False, indent=1)); return 0
    if a.cmd == 'canary':   # V11.1: explicit, opt-in trust building on public test cases (canary.enabled)
        if not dmn.ex.helpers:
            print('{"canary": "providers not configured"}'); return 1
        from canary import run as canary_run
        try:
            print(json.dumps(canary_run(dmn.ex.helpers, a.suite, provider=a.provider, project=dmn.project), ensure_ascii=False, indent=1))
        except PermissionError as e:
            print(f'ERROR: {e}', file=sys.stderr); return 2
        return 0
    if a.cmd == 'scoreboard':
        import scoreboard
        base = dmn.brain.db_path.parent
        print(json.dumps(scoreboard.build(dmn.brain, a.days, queue_db=(dmn.autonomy or {}).get('db_path'),
                                          helpers_db=base / 'helpers.sqlite3', perf_db=base / 'perf.sqlite3'),
                         ensure_ascii=False, indent=1)); return 0
    if a.cmd == 'helpers':
        h, r = dmn.ex.helpers, dmn.ex.route
        print(json.dumps({'helpers': h.stats(a.days) if h else 'not configured',
                          'routes': r.compare(a.days) if r else 'not configured'}, ensure_ascii=False, indent=1)); return 0
    import fcntl
    lock = open(dmn.brain.db_path.parent / f'daemon-{dmn.brain.identity}.lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)  # V10.1: a second instance refuses to start
    except OSError:
        print('ERROR: another daemon for this identity is already running', file=sys.stderr); return 3
    signal.signal(signal.SIGTERM, _stop); signal.signal(signal.SIGINT, _stop)
    backoff = 0
    while not STOP:
        start = time.monotonic()
        try:
            dmn.tick(); backoff = 0
        except Exception as e:  # noqa: BLE001 - a daemon must survive a bad tick
            st = dmn._state()
            dmn._save(errors=st['errors'] + 1, last_error=runner.redact(f'{type(e).__name__}: {e}')[:300])
            backoff = min(backoff * 2 + 1, 30)
            if backoff == 1 or backoff == 30:
                dmn.notice('warning', f'Fehler im Daemon-Zyklus: {type(e).__name__}')
        wait = dmn.o['tick_seconds'] * (1 + backoff) - (time.monotonic() - start)
        while wait > 0 and not STOP:
            time.sleep(min(1, wait)); wait -= 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
