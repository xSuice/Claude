#!/usr/bin/env python3
"""Fixed scenario V9 vs V10: a service fails at 02:00 in nights 1, 3 and 5 of a week.

Both versions get the same allowlisted repair action (restart) and check (state == active)
and the same simulated operator, who only acts at 08:00:
  V9   sensors + executor exist, but a deviation does not lead to work by itself: the operator
       creates and binds a repair goal for every incident.
  V10  the daemon answers deviations; after the first manual fix it proposes a procedure,
       the operator confirms it once at 08:00, later incidents are repaired locally.
Ticks every 10 min. Measures functional autonomy and time-to-recovery only - not Claude
answer quality on real tasks.
"""
from __future__ import annotations
import json, resource, statistics, sys, tempfile, time
from datetime import datetime, timedelta
from pathlib import Path

RT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RT))
from brain_core import Brain  # noqa: E402
from cognitive_loop import CognitiveLoop  # noqa: E402
from executive import Executive  # noqa: E402
from daemon import Daemon  # noqa: E402
import sensors as senses  # noqa: E402

PY = sys.executable
ACTIONS = {'actions': {
    'restart-web': {'argv': [PY, '-c', "open('web.state','w').write('active')"], 'idempotent': True},
    'web-ok': {'argv': [PY, '-c', "import sys;sys.exit(0 if open('web.state').read()=='active' else 1)"]}},
    'limits': {'max_steps_per_run': 3, 'max_local_runs_per_day': 200, 'max_attempts': 2}}
SENSORS = {'project': 'ma-home', 'sensors': [{'id': 'web', 'type': 'systemd', 'unit': 'web.service', 'severity': 4}]}
START = datetime(2026, 10, 12, 0, 0)
FAIL_NIGHTS = (1, 3, 5)


def world(tmp):
    ws = Path(tmp) / 'ws'; ws.mkdir(); (ws / 'web.state').write_text('active')
    brain = Brain(Path(tmp) / 'b.db', 'person-a', {'ma-home'})
    ex = Executive(brain, json.loads(json.dumps(ACTIONS)), ws)
    return ws, brain, ex, (lambda argv, timeout=10: (0, (ws / 'web.state').read_text()))


def manual_fix(brain, ex, proc=None):
    """What the operator does at 08:00: one goal, one bound repair step (and the link in V10)."""
    g = brain.new_goal('ma-home', 'Web reparieren', 'web aktiv', ['Dienst neu starten'], 1)
    with brain.connection() as db:
        sid = db.execute('SELECT id FROM steps WHERE goal_id=?', (g['goal_id'],)).fetchone()[0]
        aid = db.execute("SELECT id FROM cognitive_anomalies WHERE status='open' ORDER BY created DESC").fetchone()
    if proc and aid:
        proc.link(g['goal_id'], aid[0], 'sensor:web', 'failed', 'manual')
    ex.bind('ma-home', sid, 'restart-web', 'web-ok')


def simulate(version):
    with tempfile.TemporaryDirectory() as tmp:
        ws, brain, ex, run = world(tmp)
        loop = CognitiveLoop(brain)
        d = Daemon(brain, 'ma-home', ex, sensors_cfg=json.loads(json.dumps(SENSORS)), sensor_runner=run,
                   opts={'sensor_interval_seconds': 0, 'sleep_hour': 99}) if version == 'V10' else None
        human, down_since, ttr, cpu0, t0 = 0, None, [], resource.getrusage(resource.RUSAGE_CHILDREN), time.monotonic()
        t = START
        while t < START + timedelta(days=7):
            now = int(t.timestamp())
            if t.hour == 2 and t.minute == 0 and (t - START).days in FAIL_NIGHTS:
                (ws / 'web.state').write_text('failed'); down_since = now
            if version == 'V10':
                d.tick(now)
            else:
                senses.scan(loop, json.loads(json.dumps(SENSORS)), run); ex.run_once('ma-home', now)
            if t.hour == 8 and t.minute == 0:                        # the operator's morning check
                if (ws / 'web.state').read_text() != 'active':
                    manual_fix(brain, ex, d.proc if d else None); human += 1
                if d:
                    for p in d.proc.listing():
                        if p['status'] == 'proposed':
                            d.proc.set_status(p['id'], 'confirmed'); human += 1
                if version == 'V10':
                    d.tick(now)
                else:
                    ex.run_once('ma-home', now)
            if down_since and (ws / 'web.state').read_text() == 'active':
                ttr.append((now - down_since) // 60); down_since = None
            t += timedelta(minutes=10)
        cpu1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        with brain.connection() as db:
            runs = db.execute('SELECT COUNT(*) FROM exec_runs').fetchone()[0]
        return {'incidents': len(FAIL_NIGHTS), 'recovered': len(ttr), 'operator_actions': human,
                'time_to_recovery_min': ttr, 'median_ttr_min': statistics.median(ttr) if ttr else None,
                'model_calls_started': 0, 'local_process_runs': runs,
                'child_cpu_ms': int(((cpu1.ru_utime + cpu1.ru_stime) - (cpu0.ru_utime + cpu0.ru_stime)) * 1000),
                'wall_ms': int((time.monotonic() - t0) * 1000)}


if __name__ == '__main__':
    print(json.dumps({'V9': simulate('V9'), 'V10': simulate('V10')}, ensure_ascii=False, indent=1))
