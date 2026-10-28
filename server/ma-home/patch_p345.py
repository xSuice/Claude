"""Prio-1 Pakete 3-5 im Portal freischalten (Marker JARVIS-P345): Bridge + Portal erlauben
router (lesend), activity (lesend, --since), knowledge (list | approve/reject ID mit Urheber portal:<user>).
Idempotent; Backups *.bak-vor-p345-20261028."""
import ast
import shutil
from pathlib import Path


def backup(p):
    b = p.with_name(p.name + '.bak-vor-p345-20261028')
    if not b.exists():
        shutil.copy2(p, b)


br = Path('/usr/local/lib/ma-claude-bridge.py')
s = br.read_text(encoding='utf-8')
if 'JARVIS-P345' not in s:
    old = "JARVIS_SIMPLE = ('usage', 'caps', 'learned', 'meta', 'councils')"
    assert s.count(old) == 1, 'bridge simple anchor'
    s = s.replace(old, "JARVIS_SIMPLE = ('usage', 'caps', 'learned', 'meta', 'councils', 'router')")
    old2 = "    elif cmd == 'list':\n        args = ['list', '--limit',"
    assert s.count(old2) == 1, 'bridge list anchor'
    s = s.replace(old2, """    elif cmd == 'activity':                          # JARVIS-P345: Living HQ, normalisierte AgentEvents (lesend)
        args = ['activity', '--since', str(max(0, int(req.get('since') or 0)))]
    elif cmd == 'knowledge':                         # JARVIS-P345: Review-Queue des Memory-Distillers
        op, ident = str(req.get('kind') or 'list'), str(req.get('ident') or '')
        if op not in ('list', 'approve', 'reject'):
            return {'ok': False, 'error': 'Ungueltige Angabe'}
        args = ['knowledge', '--op', op]
        if op != 'list':
            who = re.sub(r'[^A-Za-z0-9._-]', '', user)[:40]
            if not who or not re.fullmatch(r'[0-9]{1,9}', ident):
                return {'ok': False, 'error': 'Freigabe ohne Benutzer oder ID'}
            args += ['--id', ident, '--by', 'portal:' + who]
""" + old2)
    ast.parse(s)
    backup(br)
    br.write_text(s, encoding='utf-8')
    print('bridge patched')
else:
    print('bridge ok')

po = Path('/opt/ma-home/portal.py')
t = po.read_text(encoding='utf-8')
if "'knowledge'," not in t:
    old = "'approve', 'revise', 'usage', 'councils',"
    assert t.count(old) == 1, 'portal anchor'
    t = t.replace(old, "'approve', 'revise', 'usage', 'councils', 'router', 'activity', 'knowledge',")
    ast.parse(t)
    backup(po)
    po.write_text(t, encoding='utf-8')
    print('portal patched')
else:
    print('portal ok')
