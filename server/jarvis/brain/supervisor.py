#!/usr/bin/env python3
"""Cost-free local supervision: polls confirmed failures; does NOT run Claude or system commands.

Use --once in Windows Task Scheduler or --interval >= 300 for a local long-running process.
"""
import argparse
import json
import signal
import time
from pathlib import Path
from brain_core import Brain
from cognitive_loop import CognitiveLoop
from observer import inspect
import sensors as senses

STOP = False

def stop(*_):
    global STOP
    STOP = True


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path,required=True)
    parser.add_argument('--once',action='store_true')
    parser.add_argument('--interval',type=int,default=1800)
    parser.add_argument('--project-root',type=Path,help='Opt-in read-only syntax scan of this folder')
    parser.add_argument('--project',help='Project grant for observations')
    parser.add_argument('--sensors',type=Path,help='V8: read-only sensor config (systemd/docker/disk/file_age/http)')
    args=parser.parse_args()
    if not args.once and args.interval<300:
        parser.error('background interval must be at least 300 seconds')
    conf=json.loads(args.config.resolve(strict=True).read_text(encoding='utf-8'))
    db=Path(conf['state_db'])
    if not db.is_absolute():db=(args.config.resolve().parent/db).resolve()
    engine=Brain(db,conf['identity'],set(conf['allowed_projects']))
    cognitive=CognitiveLoop(engine)
    signal.signal(signal.SIGINT,stop)
    if hasattr(signal,'SIGTERM'):signal.signal(signal.SIGTERM,stop)
    if args.project_root and (not args.project or args.project not in engine.projects):
        parser.error('--project-root requires a permitted --project')
    sensor_cfg=senses.load(args.sensors) if args.sensors else None
    while not STOP:
        observed=None;sensed=None
        if sensor_cfg:
            sensed=senses.scan(cognitive,sensor_cfg)
        if args.project_root and not cognitive.health(args.project)['paused']:
            observed=inspect(args.project_root)
            verified=engine.record_observation(args.project,observed)
            cognitive.observe(args.project,'test','local_python_syntax',
                f"errors:{observed['invalid']}",
                f"local parser; digest:{observed['digest'][:16]}",
                severity=4 if observed['invalid'] else 1)
        results={project:cognitive.cycle(project) for project in sorted(engine.projects)}
        print(json.dumps({'time':int(time.time()),'results':results,'observation':observed,'sensors':sensed},ensure_ascii=False),flush=True)
        if args.once:break
        # sleep in small slices, gracefully stop without heavy polling
        for _ in range(args.interval):
            if STOP:break
            time.sleep(1)

if __name__=='__main__':main()
