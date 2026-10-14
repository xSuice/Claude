#!/usr/bin/env python3
"""One real end-to-end order through the PRODUCTION path (no shortcuts):
sensor deviation -> daemon attention -> order (idempotent, risk=read, claude_budget=1) -> diagnosis
packet -> bounded queue -> real worker `autonomy.run_once` runs Claude Code -> executive polls job ->
independent local check -> step verified -> daemon harvests the answer as an UNCONFIRMED hypothesis."""
import json, sys, tempfile, time
from pathlib import Path
RT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(RT)); sys.path.insert(0, str(Path(__file__).parent))
import ab_diagnosis as ab
from brain_core import Brain
from executive import Executive
from daemon import Daemon
from autonomy import validated, Queue, run_once

t = Path(tempfile.mkdtemp()); ws = t / 'ws'; ab.build_backup_workspace(ws)
brain = Brain(t / 'state' / 'b.db', 'person-a', {'ma-home'})
auto = validated({'enabled': True, 'allowed_workspaces': [str(ws)], 'db_path': str(t / 'state' / 'q.db'),
                  'minimum_gap_seconds': 0, 'max_jobs_per_day': 1, 'allowed_templates': ['diagnosis'], 'max_turns': 8,
                  'max_run_seconds': 300, 'max_estimated_api_usd_per_run': 0.5}, t / 'a.json')
acts = {'actions': {'diagnose': {'claude_template': 'diagnosis'},
                    'packet-ok': {'argv': [sys.executable, '-c', "import glob,sys;sys.exit(0 if glob.glob('.brain/diagnosis-*.md') else 1)"]}}}
ex = Executive(brain, acts, ws, auto)
st = {'v': 'active'}
d = Daemon(brain, 'ma-home', ex, autonomy_cfg=auto, sensor_runner=lambda a, timeout=10: (0, st['v']),
           sensors_cfg={'project': 'ma-home', 'sensors': [{'id': 'backup', 'type': 'systemd', 'unit': 'backup.service',
                                                            'severity': 5, 'logs': [str(ws / 'logs' / 'backup.log')]}]},
           opts={'sensor_interval_seconds': 0, 'diagnosis': {'action': 'diagnose', 'check': 'packet-ok'}})
log = []
log.append(('tick1', d.tick())); st['v'] = 'failed'
log.append(('tick2', d.tick())); log.append(('tick3', d.tick()))
t0 = time.monotonic(); w = run_once(auto, Queue(auto['db_path'])); log.append(('worker', w))
log.append(('tick4', d.tick())); log.append(('tick5', d.tick()))
with Queue(auto['db_path']).connect() as c:
    job = dict(c.execute('SELECT status,exit_code,elapsed_ms,model_usage,result FROM jobs').fetchone())
with brain.connection() as db:
    steps = [dict(r) for r in db.execute('SELECT status,outcome FROM steps')]
    mem = [dict(r) for r in db.execute('SELECT status,kind,title FROM memory')]
    meta = [dict(r) for r in db.execute('SELECT idem_key,risk,claude_budget,claude_used FROM goal_meta')]
usage = json.loads(job['model_usage'] or '{}')
res = {'decision': log[1][1]['attention'], 'worker': w, 'job_status': job['status'], 'exit': job['exit_code'],
       'cost_usd': usage.get('total_cost_usd'), 'usage': usage.get('usage', {}), 'steps': steps, 'memory': mem,
       'order': meta, 'grade': ab.grade_backup(job['result'] or ''), 'answer_head': (job['result'] or '')[:400],
       'notices': [n['text'] for n in d.notices(limit=10)]}
print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
