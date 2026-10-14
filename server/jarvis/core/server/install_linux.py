#!/usr/bin/env python3
"""Install a central, non-root, local-only Claude Brain V5 on Linux.

No sudo, networking changes, user creation, or writes outside user-owned paths.
Dry-run unless --apply. Keeps state outside program directory.
"""
import argparse
import json
import os
import shlex
import shutil
import stat
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'brain-runtime'

def secure_dir(p):
    p.mkdir(parents=True,exist_ok=True)
    os.chmod(p,0o700)

def write_private(path, data):
    path.write_text(data, encoding='utf-8')
    os.chmod(path,0o600)

def main():
    if os.name!='posix' or not sys.platform.startswith('linux'):
        raise SystemExit('Linux only; run on your MA-Home server')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apply',action='store_true',help='Perform installation; otherwise dry-run')
    p.add_argument('--isolate-profiles',action='store_true',help='New installations: separate SQLite files per profile; OS user isolation still required')
    p.add_argument('--update',action='store_true',help='Stage new code, back up older code, keep private state')
    p.add_argument('--app-dir',type=Path,default=Path.home()/'.local/share/ma-home-brain')
    p.add_argument('--data-dir',type=Path,default=Path.home()/'.local/state/ma-home-brain')
    p.add_argument('--config-dir',type=Path,default=Path.home()/'.config/ma-home-brain')
    args=p.parse_args()
    app=args.app_dir.expanduser().absolute()
    data=args.data_dir.expanduser().absolute()
    config=args.config_dir.expanduser().absolute()
    # Do not accept symlink redirection for any target/root ancestor known to us.
    for path in (app,data,config):
        if path.is_symlink(): raise SystemExit(f'Refusing symlink path: {path}')
    if app.exists() and not args.update:
        raise SystemExit(f'{app} exists; use --update only for intentionally replacing program code')
    if app.exists() and (not app.is_dir() or app.is_symlink()):
        raise SystemExit('Existing application path is not an ordinary directory')
    print('Install target:',app)
    print('Persistent private data:',data)
    print('Profiles:',config)
    print('Users: person-a and person-b; no sample memories imported')
    print('Database profile mode:', 'separate SQLite files' if args.isolate_profiles else 'legacy shared SQLite file')
    print('Will not alter SSH, firewall, Docker, Claude settings or existing services')
    if not args.apply:
        print('DRY RUN ONLY. Supply --apply to install.')
        return 0
    if not SRC.is_dir(): raise SystemExit('brain-runtime missing')
    app.parent.mkdir(parents=True,exist_ok=True); secure_dir(data); secure_dir(config)
    # copy code into versioned staging, then atomically replace application directory
    stage=app.with_name(app.name+'.staging')
    if stage.exists():raise SystemExit(f'Staging path already exists: {stage}')
    stage.mkdir(mode=0o700)
    try:
        shutil.copytree(SRC, stage/'brain-runtime', dirs_exist_ok=True,
            ignore=shutil.ignore_patterns('__pycache__','*.pyc','.private'))
        shutil.copytree(ROOT/'humanizer-local',stage/'humanizer-local')
        shutil.copytree(ROOT/'scientific-brains',stage/'scientific-brains',
            ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        secure_dir(stage/'bin')
        for identity in ('person-a','person-b'):
            profile=config/(identity+'.json')
            if not profile.exists():
                write_private(profile,json.dumps({
                    'identity':identity,'allowed_projects':['ma-home'],
                    'state_db':str(data / (('brain-'+identity+'.sqlite3') if args.isolate_profiles else 'brain.sqlite3')),
                    'research_tools':False
                },ensure_ascii=False,indent=2)+'\n')
            script=(stage/'bin'/('mcp-'+identity))
            text='#!/bin/sh\nset -eu\nexec '+ ' '.join(map(shlex.quote, [sys.executable,
                str(app/'brain-runtime/mcp_server_v5.py'), '--config',str(profile)]))+'\n'
            script.write_text(text,encoding='utf-8');os.chmod(script,0o700)
        if app.exists():
            from datetime import datetime,timezone
            backup=app.with_name(app.name+'.backup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
            if backup.exists():raise SystemExit('Backup target unexpectedly exists')
            app.rename(backup)
            print('Old application code backup:',backup)
        try:
            stage.rename(app)
        except Exception:
            if 'backup' in locals() and backup.exists() and not app.exists():
                backup.rename(app)
            raise
    finally:
        if stage.exists(): shutil.rmtree(stage)
    print('INSTALLED (user-only, localhost/SSH launch, no new listener)')
    print('Test:',shlex.join([sys.executable,str(app/'brain-runtime/supervisor.py'),
        '--config',str(config/'person-a.json'),'--once']))
    print('SSH forced commands:')
    for identity in ('person-a','person-b'):
        print(identity+': restrict,command="'+str(app/'bin'/('mcp-'+identity))+'" ssh-ed25519 <PERSON_PUBLIC_KEY>')
    print('Do not paste placeholder keys; install actual authorized_keys lines securely.')
    return 0
if __name__=='__main__':
    raise SystemExit(main())
