"""Paket 8 im Portal (Marker JARVIS-P8): Bridge + Portal erlauben audit (lesend) und Not-Aus-Stufen (kind=soft|exec|hard).
Idempotent; Backups *.bak-vor-p8-20261028."""
import ast
import shutil
from pathlib import Path


def backup(p):
    b = p.with_name(p.name + '.bak-vor-p8-20261028')
    if not b.exists():
        shutil.copy2(p, b)


br = Path('/usr/local/lib/ma-claude-bridge.py')
s = br.read_text(encoding='utf-8')
if 'JARVIS-P8' not in s:
    old = "JARVIS_SIMPLE = ('usage', 'caps', 'learned', 'meta', 'councils', 'router')"
    assert s.count(old) == 1, 'bridge simple anchor'
    s = s.replace(old, "JARVIS_SIMPLE = ('usage', 'caps', 'learned', 'meta', 'councils', 'router', 'audit')")
    old2 = "        args = ['kill', 'on' if req.get('state') == 'on' else 'off']"
    assert s.count(old2) == 1, 'bridge kill anchor'
    s = s.replace(old2, """        args = ['kill', 'on' if req.get('state') == 'on' else 'off']
        if req.get('state') == 'on' and str(req.get('kind') or '') in ('soft', 'exec', 'hard'):   # JARVIS-P8: Not-Aus-Stufe
            args += ['--level', str(req['kind'])]""")
    ast.parse(s)
    backup(br)
    br.write_text(s, encoding='utf-8')
    print('bridge patched')
else:
    print('bridge ok')

po = Path('/opt/ma-home/portal.py')
t = po.read_text(encoding='utf-8')
if "'audit'," not in t:
    old = "'councils', 'router', 'activity', 'knowledge',"
    assert t.count(old) == 1, 'portal anchor'
    t = t.replace(old, "'councils', 'router', 'activity', 'knowledge', 'audit',")
    ast.parse(t)
    backup(po)
    po.write_text(t, encoding='utf-8')
    print('portal patched')
else:
    print('portal ok')
