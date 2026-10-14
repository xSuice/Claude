#!/usr/bin/env python3
"""Optional event-driven proposal -> bounded read-only audit job.

Requires an already enabled V6 autonomy allowlist and --enqueue. Default dry-run.
Never runs Claude itself. A separate operator-enabled worker does that.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from brain_core import Brain
from cognitive_loop import CognitiveLoop
from autonomy import Queue, load_config


def prepare(loop: CognitiveLoop, cfg: dict, project: str, workspace: str, enqueue=False):
    """Enqueue at most one audit per distinct high-severity anomaly; no shell/LLM."""
    if loop.health(project)['paused']:
        return {'created':[],'blocked':'paused'}
    workspace=str(Path(workspace).expanduser().resolve(strict=True))
    if workspace not in cfg['allowed_workspaces']:
        raise PermissionError('workspace not allowlisted')
    if 'repo_audit' not in cfg['allowed_templates']:
        raise PermissionError('repo_audit template not allowlisted')
    # V7.1: query severe anomalies directly; the 3-item focus list could hide them behind goals.
    triggered=loop.severe_anomalies(project,4)
    with loop.brain.connection(True) as db:
        db.execute('''CREATE TABLE IF NOT EXISTS cognitive_initiatives (
            owner TEXT NOT NULL, project TEXT NOT NULL, anomaly TEXT NOT NULL,
            workspace TEXT NOT NULL, job_id TEXT NOT NULL, created INTEGER NOT NULL,
            PRIMARY KEY(owner,project,anomaly,workspace))''')
    pending=[]
    with loop.brain.connection() as db:
        for item in triggered:
            row=db.execute('SELECT job_id FROM cognitive_initiatives WHERE owner=? AND project=? '
                           'AND anomaly=? AND workspace=?',
                           (loop.brain.identity,project,item['anomaly_id'],workspace)).fetchone()
            if row is None:
                pending.append(item)
    if not enqueue:
        return {'created':[],'dry_run':True,'eligible':len(pending),
                'note':'No Claude calls. Use --enqueue only for pre-approved read-only audits.'}
    if not cfg['enabled']:
        return {'created':[],'blocked':'autonomy disabled'}
    queue=Queue(cfg['db_path'])
    created=[]
    for item in pending[:1]:  # one audit at a time, avoid excessive model work
        job_id=queue.enqueue(cfg,loop.brain.identity,project,'repo_audit',workspace)
        import time
        with loop.brain.connection(True) as db:
            cur=db.execute('INSERT OR IGNORE INTO cognitive_initiatives '
                           '(owner,project,anomaly,workspace,job_id,created) VALUES(?,?,?,?,?,?)',
                           (loop.brain.identity,project,item['anomaly_id'],workspace,job_id,int(time.time())))
            if cur.rowcount:
                created.append({'job_id':job_id,'anomaly_id':item['anomaly_id']})
    return {'created':created,'pending_cloud_jobs':len(created),
            'note':'Queued read-only audit only. Worker must be separately enabled and run.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--brain-config',type=Path,required=True)
    p.add_argument('--autonomy-config',type=Path,required=True)
    p.add_argument('--project',required=True)
    p.add_argument('--workspace',required=True)
    p.add_argument('--enqueue',action='store_true',help='Opt-in only: enqueue, does NOT run Claude')
    args=p.parse_args()
    try:
        bp=args.brain_config.resolve(strict=True)
        conf=json.loads(bp.read_text(encoding='utf-8'))
        db=Path(conf['state_db']).expanduser()
        if not db.is_absolute():db=(bp.parent/db).resolve()
        cog=CognitiveLoop(Brain(db,conf['identity'],set(conf['allowed_projects'])))
        cfg=load_config(args.autonomy_config)
        print(json.dumps(prepare(cog,cfg,args.project,args.workspace,args.enqueue),ensure_ascii=False))
        return 0
    except (OSError,PermissionError,ValueError,KeyError) as err:
        p.exit(2,f'ERROR: {err}\n')

if __name__=='__main__':raise SystemExit(main())
