#!/usr/bin/env python3
"""V10.1 consistent backup of all brain state + configs, with a mandatory restore probe.

backup   SQLite online-backup API for every database (brain, queue; the vault index is
         derivable and skipped), copies of the configs, SHA-256 manifest, one owner-only
         tar.gz. Then it immediately restores into a temp dir and compares integrity_check
         and per-table row counts with the live databases - a backup that cannot be
         restored is reported as failed.
restore  Unpacks an archive into an EMPTY target directory (never over live files),
         verifies the manifest and runs integrity_check. Switching paths is a manual step.
Usage:
  python3 server/backup_restore.py backup  --config brain.json [--extra autonomy.json ...] --out DIR
  python3 server/backup_restore.py restore --archive FILE --to EMPTY_DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import tarfile
import tempfile
import time
from pathlib import Path


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def _counts(db: Path) -> dict:
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    try:
        tabs = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                                        "AND sql NOT LIKE 'CREATE VIRTUAL%'")]
        out = {}
        for t in tabs:
            try:
                out[t] = c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            except sqlite3.DatabaseError:
                pass  # FTS shadow tables etc.
        return out
    finally:
        c.close()


def _integrity(db: Path) -> str:
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    try:
        return c.execute('PRAGMA integrity_check').fetchone()[0]
    finally:
        c.close()


def collect(config: Path, extra: list[Path]) -> tuple[dict, dict]:
    """Return ({name: db_path}, {name: config_path}) from the brain config and extra configs."""
    dbs, cfgs = {}, {}
    for cfg in [config, *extra]:
        cfg = cfg.expanduser().resolve(strict=True)
        cfgs[cfg.name] = cfg
        d = json.loads(cfg.read_text(encoding='utf-8'))
        for key in ('state_db', 'db_path'):
            if d.get(key):
                p = Path(d[key]).expanduser()
                p = p if p.is_absolute() else (cfg.parent / p).resolve()
                if p.exists():
                    dbs[f'{cfg.stem}.{key}.sqlite3'] = p
        for key in ('actions', 'sensors', 'autonomy_config', 'brain_config'):
            if isinstance(d.get(key), str):
                p = Path(d[key]).expanduser()
                p = p if p.is_absolute() else (cfg.parent / p).resolve()
                if p.is_file():
                    cfgs.setdefault(p.name, p)
    return dbs, cfgs


def backup(config: Path, extra: list[Path], out_dir: Path) -> dict:
    os.umask(0o077)
    out_dir = out_dir.expanduser(); out_dir.mkdir(parents=True, exist_ok=True); os.chmod(out_dir, 0o700)
    dbs, cfgs = collect(config, extra)
    stamp = time.strftime('%Y%m%d-%H%M%S')
    with tempfile.TemporaryDirectory() as t:
        stage = Path(t) / f'brain-backup-{stamp}'; (stage / 'db').mkdir(parents=True); (stage / 'config').mkdir()
        live_counts = {}
        for name, src in dbs.items():
            s = sqlite3.connect(f'file:{src}?mode=ro', uri=True); d = sqlite3.connect(stage / 'db' / name)
            try:
                s.backup(d)                       # consistent snapshot even while the daemon writes
            finally:
                d.close(); s.close()
            live_counts[name] = _counts(stage / 'db' / name)
        for name, src in cfgs.items():
            shutil.copy2(src, stage / 'config' / name)
        manifest = {'created': stamp, 'sources': {k: str(v) for k, v in {**dbs, **cfgs}.items()},
                    'sha256': {str(p.relative_to(stage)): _sha(p) for p in stage.rglob('*') if p.is_file()},
                    'row_counts': live_counts}
        (stage / 'MANIFEST.json').write_text(json.dumps(manifest, indent=1))
        archive = out_dir / f'{stage.name}.tar.gz'
        with tarfile.open(archive, 'w:gz') as tar:
            tar.add(stage, arcname=stage.name)
    os.chmod(archive, 0o600)
    probe = restore(archive, Path(tempfile.mkdtemp(prefix='brain-restore-probe-')), cleanup=True)
    ok = probe['ok'] and all(probe['row_counts'].get(k) == v for k, v in live_counts.items())
    return {'archive': str(archive), 'bytes': archive.stat().st_size, 'databases': list(dbs), 'configs': list(cfgs),
            'restore_probe_ok': ok, 'probe': probe}


def restore(archive: Path, to: Path, cleanup=False) -> dict:
    to = to.expanduser()
    if to.exists() and any(to.iterdir()):
        raise FileExistsError('restore target must be empty (live files are never overwritten)')
    to.mkdir(parents=True, exist_ok=True); os.chmod(to, 0o700)
    try:
        with tarfile.open(archive, 'r:gz') as tar:
            tar.extractall(to, filter='data')     # refuses absolute paths, '..', devices, links out
        root = next(p for p in to.iterdir() if p.is_dir())
        man = json.loads((root / 'MANIFEST.json').read_text())
        bad = [k for k, v in man['sha256'].items() if _sha(root / k) != v]
        dbs = sorted((root / 'db').glob('*.sqlite3'))
        integ = {p.name: _integrity(p) for p in dbs}
        counts = {p.name: _counts(p) for p in dbs}
        return {'ok': not bad and all(v == 'ok' for v in integ.values()), 'hash_mismatch': bad,
                'integrity': integ, 'row_counts': counts, 'restored_to': None if cleanup else str(root)}
    finally:
        if cleanup:
            shutil.rmtree(to, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('backup'); b.add_argument('--config', type=Path, required=True)
    b.add_argument('--extra', type=Path, action='append', default=[]); b.add_argument('--out', type=Path, required=True)
    r = sub.add_parser('restore'); r.add_argument('--archive', type=Path, required=True); r.add_argument('--to', type=Path, required=True)
    a = ap.parse_args()
    out = backup(a.config, a.extra, a.out) if a.cmd == 'backup' else restore(a.archive, a.to)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out.get('restore_probe_ok', out.get('ok')) else 1


if __name__ == '__main__':
    raise SystemExit(main())
