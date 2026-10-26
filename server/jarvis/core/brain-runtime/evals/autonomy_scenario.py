#!/usr/bin/env python3
"""Fixed capability scenario V8 vs V9: one maintenance goal, a crash, a step that always fails.

Scenario (unchanged between versions):
  1 Konfiguration erzeugen   idempotent local action, check: file exists
  2 Zähler/Backup-Marker     NOT idempotent; the worker "crashes" while it runs
  3 Selbsttest               local action, check passes
  4 Defekte Aufgabe          check always fails
V8 has goals/steps but no executor: every step needs a Claude/human session to be carried
out and reported. V9 runs the steps from a timer. Measures functional autonomy only - not
answer quality of Claude on real tasks.
"""
from __future__ import annotations
import json, resource, sys, tempfile, time
from pathlib import Path

RT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RT))
from brain_core import Brain  # noqa: E402
from executive import Executive  # noqa: E402

PY = sys.executable
STEPS = ['Konfiguration erzeugen', 'Backup-Marker schreiben', 'Selbsttest', 'Defekte Aufgabe']
ACTIONS = {'actions': {
    'gen-config': {'argv': [PY, '-c', "open('config.ini','w').write('[x]')"], 'idempotent': True},
    'has-config': {'argv': [PY, '-c', "import os,sys;sys.exit(0 if os.path.exists('config.ini') else 1)"]},
    'marker': {'argv': [PY, '-c', "import pathlib;p=pathlib.Path('marker');p.write_text(p.read_text()+'x' if p.exists() else 'x')"]},
    'has-marker': {'argv': [PY, '-c', "import pathlib,sys;sys.exit(0 if pathlib.Path('marker').read_text()=='x' else 1)"]},
    'selftest': {'argv': [PY, '-c', "print('ok')"], 'idempotent': True},
    'broken': {'argv': [PY, '-c', "import sys;sys.exit(2)"]}},
    'limits': {'max_steps_per_run': 3, 'max_local_runs_per_day': 60, 'max_attempts': 2}}
BIND = [('gen-config', 'has-config'), ('marker', 'has-marker'), ('selftest', 'selftest'), ('selftest', 'broken')]


def v8_baseline() -> dict:
    """V8: next_step only proposes; nothing runs until a session acts on each step."""
    with tempfile.TemporaryDirectory() as t:
        b = Brain(Path(t) / 'b.db', 'person-a', {'ma-home'})
        b.new_goal('ma-home', 'Wartung', 'alles erledigt', STEPS)
        nxt = b.next_step('ma-home')
        return {'steps_verified_without_session': 0, 'sessions_needed_at_least': len(STEPS),
                'next_step_proposed': nxt.get('instruction'), 'independent_check': False,
                'resume_after_crash': 'manual', 'model_calls_started': 0}


def v9_run() -> dict:
    with tempfile.TemporaryDirectory() as t:
        d = Path(t); ws = d / 'ws'; ws.mkdir()
        b = Brain(d / 'b.db', 'person-a', {'ma-home'})
        g = b.new_goal('ma-home', 'Wartung', 'alles erledigt', STEPS)
        ex = Executive(b, json.loads(json.dumps(ACTIONS)), ws)
        with b.connection() as db:
            ids = [r[0] for r in db.execute('SELECT id FROM steps WHERE goal_id=? ORDER BY ordinal', (g['goal_id'],))]
        for sid, (a, c) in zip(ids, BIND):
            ex.bind('ma-home', sid, a, c)
        t0, cpu0 = time.monotonic(), resource.getrusage(resource.RUSAGE_CHILDREN)
        now, ticks, log = int(time.time()), 0, []
        ex.run_once('ma-home', now)                       # tick 1: step 1 verified
        with b.connection(True) as db:                    # tick 2 "crashes" during step 2
            db.execute("UPDATE exec_bindings SET state='running',lease_until=? WHERE step_id=?", (now + 60, ids[1]))
        (ws / 'marker').write_text('x')                   # the crashed run had already written its marker
        ticks = 1
        for k in range(1, 8):                             # timer keeps ticking after the reboot
            r = ex.run_once('ma-home', now + 900 * k); ticks += 1
            log.append({k: [(x['step_id'][:6], x.get('state')) for x in r['executed']], 'reconciled': len(r['reconciled'])})
        cpu1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        with b.connection() as db:
            st = {r['ordinal']: (r['status'], r['attempts']) for r in db.execute(
                'SELECT ordinal,status,attempts FROM steps WHERE goal_id=?', (g['goal_id'],))}
            runs = db.execute('SELECT COUNT(*) FROM exec_runs').fetchone()[0]
        return {'step_status': {STEPS[o - 1]: s for o, s in st.items()},
                'steps_verified_without_session': sum(1 for s, _ in st.values() if s == 'verified'),
                'steps_blocked_for_review': sum(1 for s, _ in st.values() if s == 'blocked'),
                'non_idempotent_rerun_after_crash': (ws / 'marker').read_text() != 'x',
                'local_process_runs': runs, 'timer_ticks': ticks, 'model_calls_started': 0,
                'wall_ms': int((time.monotonic() - t0) * 1000),
                'child_cpu_ms': int(((cpu1.ru_utime + cpu1.ru_stime) - (cpu0.ru_utime + cpu0.ru_stime)) * 1000)}


if __name__ == '__main__':
    print(json.dumps({'V8': v8_baseline(), 'V9': v9_run()}, ensure_ascii=False, indent=1))
