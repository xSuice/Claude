"""Councils freischalten (Marker JARVIS-ROUTER): Bridge + Portal erlauben cmd 'councils' (nur lesend), jarvis.json council.enabled.
Idempotent; Backups *.bak-vor-router-20261028."""
import ast, json, os, shutil
from pathlib import Path


def backup(p):
    b = p.with_name(p.name + '.bak-vor-router-20261028')
    if not b.exists():
        shutil.copy2(p, b)


br = Path('/usr/local/lib/ma-claude-bridge.py')
s = br.read_text(encoding='utf-8')
if "'router'" not in s:
    old = "JARVIS_SIMPLE = ('usage', 'caps', 'learned', 'meta', 'councils')"
    assert s.count(old) == 1, 'bridge anchor'
    s2 = s.replace(old, "JARVIS_SIMPLE = ('usage', 'caps', 'learned', 'meta', 'councils', 'router')")
    ast.parse(s2); backup(br); br.write_text(s2, encoding='utf-8'); print('bridge patched')
else:
    print('bridge ok')
po = Path('/opt/ma-home/portal.py')
t = po.read_text(encoding='utf-8')
if "'router'," not in t:
    old = "'approve', 'revise', 'usage', 'councils',"
    assert t.count(old) == 1, 'portal anchor'
    t2 = t.replace(old, "'approve', 'revise', 'usage', 'councils', 'router',")
    ast.parse(t2); backup(po); po.write_text(t2, encoding='utf-8'); print('portal patched')
else:
    print('portal ok')
