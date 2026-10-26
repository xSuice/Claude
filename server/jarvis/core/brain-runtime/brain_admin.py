#!/usr/bin/env python3
"""Explicit local operator actions. Deliberately NOT available over the Claude MCP interface."""
import argparse
import json
from pathlib import Path
from brain_core import Brain


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path,required=True)
    sub=p.add_subparsers(dest='action',required=True)
    a=sub.add_parser('pending');a.add_argument('project')
    a=sub.add_parser('confirm');a.add_argument('record');a.add_argument('--supersede')
    a.add_argument('--share-with',action='append',default=[],help='Explicitly authorized recipients')
    a=sub.add_parser('retract');a.add_argument('record')
    a=sub.add_parser('verify-episode');a.add_argument('event')
    a=sub.add_parser('insights');a.add_argument('project')
    a=sub.add_parser('goals');a.add_argument('project')
    a=sub.add_parser('tick');a.add_argument('project')
    args=p.parse_args()
    config=json.loads(args.config.resolve(strict=True).read_text(encoding='utf-8'))
    db=Path(config['state_db'])
    if not db.is_absolute():db=(args.config.resolve().parent/db).resolve()
    brain=Brain(db,config['identity'],set(config['allowed_projects']))
    result={'pending':lambda:brain.pending(args.project),
            'confirm':lambda:brain.confirm(args.record,supersede=args.supersede,recipients=args.share_with),
            'retract':lambda:brain.retract(args.record),
            'verify-episode':lambda:brain.verify_episode(args.event),
            'insights':lambda:brain.insights(args.project),
            'goals':lambda:brain.list_goals(args.project),
            'tick':lambda:brain.tick(args.project)}[args.action]()
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
