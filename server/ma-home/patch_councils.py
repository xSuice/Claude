"""Councils freischalten (Marker JARVIS-COUNCILS): Bridge + Portal erlauben cmd 'councils' (nur lesend), jarvis.json council.enabled.
Idempotent; Backups *.bak-vor-councils-20261028."""
import ast, json, os, shutil
from pathlib import Path


def backup(p):
    b = p.with_name(p.name + '.bak-vor-councils-20261028')
    if not b.exists():
        shutil.copy2(p, b)


br = Path('/usr/local/lib/ma-claude-bridge.py')
s = br.read_text(encoding='utf-8')
if "'councils'" not in s:
    old = "JARVIS_SIMPLE = ('usage', 'caps', 'learned', 'meta')"
    assert s.count(old) == 1, 'bridge anchor'
    s2 = s.replace(old, "JARVIS_SIMPLE = ('usage', 'caps', 'learned', 'meta', 'councils')  # JARVIS-COUNCILS")
    ast.parse(s2); backup(br); br.write_text(s2, encoding='utf-8'); print('bridge patched')
else:
    print('bridge ok')
po = Path('/opt/ma-home/portal.py')
t = po.read_text(encoding='utf-8')
if "'councils'" not in t:
    old = "'approve', 'revise', 'usage',"
    assert t.count(old) == 1, 'portal anchor'
    t2 = t.replace(old, "'approve', 'revise', 'usage', 'councils',")
    ast.parse(t2); backup(po); po.write_text(t2, encoding='utf-8'); print('portal patched')
else:
    print('portal ok')
cf = Path('/home/andrew/.config/ma-jarvis/jarvis.json')
c = json.loads(cf.read_text(encoding='utf-8'))
if not (c.get('council') or {}).get('enabled'):
    backup(cf)
    c['council'] = {'enabled': True, 'max_roles': 3, 'model': 'haiku'}
    tmp = cf.with_name(cf.name + '.tmp')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as fh:
        json.dump(c, fh, indent=1)
    os.replace(tmp, cf)
    print('config: council enabled')
else:
    print('config ok')
