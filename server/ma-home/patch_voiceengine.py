"""Idempotent patcher (MA-HOME, 2026-10-27): long browser cache for versioned voice-engine vendor files + CSP wasm-unsafe-eval.
Run with sudo on ma-server. Backs up every file it touches (*.bak-vor-voiceengine-20261027)."""
import ast, re, shutil, sys
from pathlib import Path

TAG = 'bak-vor-voiceengine-20261027'


def backup(p):
    b = p.with_name(p.name + '.' + TAG)
    if not b.exists():
        shutil.copy2(p, b)


# 1) portal.py: Cache-Control for /staging/js/vendor/* (files live in versioned folders ort-1.22.0/, oww-0.5.1/, vad-0.0.31/)
portal = Path('/opt/ma-home/portal.py')
s = portal.read_text(encoding='utf-8')
if 'VENDOR-CACHE' not in s:
    old = "    response.headers['Cache-Control'] = 'no-store'\n    response.headers['X-Content-Type-Options'] = 'nosniff'"
    assert s.count(old) == 1, 'anchor after_request'
    new = ("    # VENDOR-CACHE: versionierte Sprach-Engine-Dateien (WASM 11 MB, Modelle) privat cachen, alles andere no-store\n"
           "    if request.path.startswith('/staging/js/vendor/') and response.status_code == 200:\n"
           "        response.headers['Cache-Control'] = 'private, max-age=2592000, immutable'\n"
           "    else:\n"
           "        response.headers['Cache-Control'] = 'no-store'\n"
           "    response.headers['X-Content-Type-Options'] = 'nosniff'")
    s2 = s.replace(old, new)
    ast.parse(s2)
    backup(portal)
    portal.write_text(s2, encoding='utf-8')
    print('portal.py patched')
else:
    print('portal.py already patched')

# 2) CSP: allow WebAssembly compilation only ('wasm-unsafe-eval' does NOT allow JS eval)
OLD = "script-src 'self';"
NEW = "script-src 'self' 'wasm-unsafe-eval';"
for p in (Path('/etc/ma-home/Caddyfile'), Path('/opt/ma-home/manage.py')):
    t = p.read_text(encoding='utf-8')
    if NEW in t:
        print(p, 'already patched')
        continue
    n = t.count(OLD)
    assert n == 1, f'{p}: {n} CSP anchors'
    backup(p)
    t2 = t.replace(OLD, NEW)
    if p.suffix == '.py':
        ast.parse(t2)
    p.write_text(t2, encoding='utf-8')
    print(p, 'patched')
