#!/usr/bin/env python3
"""Consistent hot backup for SQLite, using its online backup API."""
import argparse
import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

def main():
    os.umask(0o077)  # V10.1: backup files never exist with group/world rights, not even briefly
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--out-dir',type=Path,required=True)
    args=p.parse_args()
    cfg=json.loads(args.config.read_text(encoding='utf-8'))
    db=Path(cfg['state_db'])
    if not db.is_absolute(): db=(args.config.parent/db).resolve()
    if not db.is_file(): raise SystemExit('DB not initialized; run MCP or supervisor once first')
    out=args.out_dir.expanduser().absolute()
    out.mkdir(parents=True,exist_ok=True)
    os.chmod(out,0o700)
    dst=out/('brain-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.sqlite3')
    try:
        with sqlite3.connect(f'file:{db}?mode=ro',uri=True) as src:
            with sqlite3.connect(dst) as target:
                src.backup(target)
        os.chmod(dst,0o600)
        with sqlite3.connect(dst) as chk:
            status=chk.execute('PRAGMA integrity_check').fetchone()[0]
            if status!='ok': raise RuntimeError('SQLite integrity check failed: '+status)
    except Exception:
        dst.unlink(missing_ok=True)
        raise
    print('SQLite backup verified:',dst)
if __name__=='__main__': main()
