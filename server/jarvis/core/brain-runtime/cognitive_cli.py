#!/usr/bin/env python3
"""Trusted local CLI for cognitive events and expectations. No shell/model/network."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from brain_core import Brain
from cognitive_loop import CognitiveLoop, EVENT_TYPES


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True)
    cmd=p.add_subparsers(dest='action',required=True)
    for action in ('health','focus','cycle','consolidate','pause','resume'):
        z=cmd.add_parser(action);z.add_argument('--project',required=True)
    a=cmd.add_parser('expect');a.add_argument('--project',required=True)
    a.add_argument('--subject',required=True);a.add_argument('--expected',required=True)
    a.add_argument('--evidence',required=True);a.add_argument('--ttl-hours',type=int,default=24)
    o=cmd.add_parser('observe');o.add_argument('--project',required=True)
    o.add_argument('--kind',required=True,choices=sorted(EVENT_TYPES));o.add_argument('--subject',required=True)
    o.add_argument('--value',required=True);o.add_argument('--source',required=True)
    o.add_argument('--severity',type=int,default=2)
    args=p.parse_args()
    try:
        cfgpath=args.config.resolve(strict=True)
        cfg=json.loads(cfgpath.read_text(encoding='utf-8'))
        raw=Path(cfg['state_db']).expanduser()
        db=raw if raw.is_absolute() else (cfgpath.parent/raw).resolve()
        loop=CognitiveLoop(Brain(db,cfg['identity'],set(cfg['allowed_projects'])))
        if args.action=='health': result=loop.health(args.project)
        elif args.action=='focus': result=loop.focus(args.project)
        elif args.action=='cycle': result=loop.cycle(args.project)
        elif args.action=='consolidate': result=loop.consolidate(args.project)
        elif args.action in ('pause','resume'):result=loop.set_paused(args.project,args.action=='pause')
        elif args.action=='expect':result=loop.expectation(args.project,args.subject,args.expected,
                                                 args.evidence,args.ttl_hours)
        elif args.action=='observe':result=loop.observe(args.project,args.kind,args.subject,
                                                args.value,args.source,args.severity)
        else: raise ValueError('unknown action')
        print(json.dumps(result,ensure_ascii=False))
        return 0
    except (ValueError,KeyError,PermissionError,OSError) as exc:
        print(f'ERROR: {type(exc).__name__}: {exc}',file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
