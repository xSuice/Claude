#!/usr/bin/env python3
"""Offline 'senses': bounded, read-only syntax observations of approved local projects.

Never executes scanned code, never reads .env, never emits contents. A failed parse
is *not* a conclusion about runtime correctness or security.
"""
from __future__ import annotations
import ast
import hashlib
import json
import os
from pathlib import Path

SKIP = {'.git','.venv','venv','node_modules','__pycache__','build','dist',
        '.next','vendor','.cache','.private','coverage'}
EXTS={'.py','.json'}


def inspect(root: Path, max_files=350, max_size=100_000) -> dict:
    root=Path(root).resolve(strict=True)
    if not root.is_dir():raise ValueError('project path must be a directory')
    if not (1<=max_files<=2000 and 1024<=max_size<=1_000_000):raise ValueError('limits out of range')
    checked=0;errors=[];skipped=0
    digest=hashlib.sha256()
    # os.walk does not follow symlinked directories by default; reject symlinked files too.
    for directory, dirs, files in os.walk(root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if d not in SKIP and not (Path(directory)/d).is_symlink())
        for name in sorted(files):
            if checked>=max_files:break
            path=Path(directory)/name
            if path.suffix.lower() not in EXTS or path.is_symlink():continue
            if not path.resolve().is_relative_to(root):continue
            try:
                if path.stat().st_size>max_size:
                    skipped+=1;continue
                raw=path.read_bytes()
            except OSError:
                skipped+=1;continue
            # utf-8 only: lint error if malformed; never execute anything.
            relative=path.relative_to(root).as_posix()
            digest.update(relative.encode('utf-8')+b'\0'+hashlib.sha256(raw).digest())
            checked+=1
            try:
                data=raw.decode('utf-8-sig')
                if path.suffix.lower()=='.py':ast.parse(data,filename=relative)
                else:json.loads(data)
            except (UnicodeError,ValueError,SyntaxError) as exc:
                errors.append({'file':relative,'kind':type(exc).__name__})
        if checked>=max_files:break
    return {'checked':checked,'invalid':len(errors),'errors':errors[:12],
            'skipped_oversize_or_unreadable':skipped,'limit_reached':checked==max_files,
            'digest':digest.hexdigest(),
            'scope':'Python AST / JSON syntax only, not a code, runtime, security, or functional test.'}
