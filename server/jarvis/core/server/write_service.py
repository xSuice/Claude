#!/usr/bin/env python3
"""Create (not enable) the non-root systemd user service for local supervision."""
import argparse
import os
import sys
from pathlib import Path

def quoted(value):
    value=str(value)
    if any(x in value.replace('%i','') for x in ('\n','\r','"','\\','%')):
        raise ValueError('Unsupported path characters (newline, quote, backslash, percent)')
    return '"'+value+'"'

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--app-dir',type=Path,default=Path.home()/'.local/share/ma-home-brain')
    p.add_argument('--config-dir',type=Path,default=Path.home()/'.config/ma-home-brain')
    p.add_argument('--apply',action='store_true')
    a=p.parse_args()
    app=a.app_dir.expanduser().absolute()
    cfg=a.config_dir.expanduser().absolute()
    if not (app/'brain-runtime/supervisor.py').is_file():
        raise SystemExit('Install the server first')
    unit=Path.home()/'.config/systemd/user/ma-home-brain@.service'
    service=(
        '[Unit]\nDescription=MA-Home Cognitive Brain supervisor (%i)\n'
        'After=local-fs.target\n\n[Service]\nType=simple\n'
        'ExecStart='+quoted(sys.executable)+' '+quoted(app/'brain-runtime/supervisor.py')+
        ' --config '+quoted(cfg/'%i.json')+' --interval 1800\n'
        'Restart=on-failure\nRestartSec=30\n'
        'NoNewPrivileges=true\nMemoryMax=350M\nCPUQuota=50%\n'
        'WorkingDirectory='+quoted(app)+'\n\n[Install]\nWantedBy=default.target\n'
    )
    print('Unit:',unit)
    print(service)
    if a.apply:
        unit.parent.mkdir(parents=True,exist_ok=True)
        if unit.exists():raise SystemExit('Unit exists; refusing overwrite')
        unit.write_text(service,encoding='utf-8')
        os.chmod(unit,0o600)
        print('CREATED (not enabled); run systemctl --user daemon-reload, then enable the specific profile')
    else:print('DRY RUN: use --apply to write unit')
if __name__=='__main__':main()
