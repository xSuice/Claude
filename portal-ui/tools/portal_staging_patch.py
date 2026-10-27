#!/usr/bin/env python3
"""Fuegt /staging/-Route in portal.py ein (M1). Idempotent."""
import pathlib, sys

p = pathlib.Path("/opt/ma-home/portal.py")
src = p.read_text(encoding="utf-8")

MARK = "@app.get('/staging')"

if MARK in src:
    print("bereits vorhanden — keine Aenderung")
    sys.exit(0)

ANCHOR = "@app.get('/api/me')"
BLOCK = '''# --- MA-HOME HQ Staging (M1, 2026-10-27): Designsystem-Neuaufbau ---
@app.get('/staging')
@app.get('/staging/')
def staging_index():
    return send_from_directory(STATIC / 'staging', 'index.html')


@app.get('/staging/<path:name>')
def staging_files(name):
    return send_from_directory(STATIC / 'staging', name)


'''

if ANCHOR not in src:
    print("ANKER NICHT GEFUNDEN", file=sys.stderr)
    sys.exit(1)

src = src.replace(ANCHOR, BLOCK + ANCHOR, 1)
p.write_text(src, encoding="utf-8")
print("gepatcht")
