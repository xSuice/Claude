"""Bridge: JARVIS cmd 'revise' (marker JARVIS-REVISE). Idempotent, Backup *.bak-vor-revise-20261028."""
import ast, shutil
from pathlib import Path
p = Path('/usr/local/lib/ma-claude-bridge.py')
s = p.read_text(encoding='utf-8')
if 'JARVIS-REVISE' in s:
    print('bridge already patched'); raise SystemExit
a = """    elif cmd == 'list':
        args = ['list', '--limit', str(min(50, max(1, int(req.get('limit') or 20))))]"""
assert s.count(a) == 1, 'anchor'
s = s.replace(a, """    elif cmd == 'revise':                            # JARVIS-REVISE: Auftrag aendern (gleiche ID, neue Revision), Urheber = Portal-Benutzer
        if not JARVIS_JOB.fullmatch(job):
            return {'ok': False, 'error': 'Ungueltige Auftrags-ID'}
        text = str(req.get('request') or '').strip()
        if not 3 <= len(text) <= 8000:
            return {'ok': False, 'error': 'Aenderung leer oder laenger als 8000 Zeichen'}
        who = re.sub(r'[^A-Za-z0-9._-]', '', user)[:40]
        if not who:
            return {'ok': False, 'error': 'Aenderung ohne bekannten Portal-Benutzer'}
        args = ['revise', job, '--change', text, '--by', 'portal:' + who]
        exp = req.get('expected')
        if isinstance(exp, int) and exp > 0:
            args += ['--expected', str(exp)]
""" + a)
ast.parse(s)
b = p.with_name(p.name + '.bak-vor-revise-20261028')
if not b.exists():
    shutil.copy2(p, b)
p.write_text(s, encoding='utf-8')
print('bridge patched')
q = Path('/opt/ma-home/portal.py')
t = q.read_text(encoding='utf-8')
old = "if cmd not in ('submit', 'list', 'status', 'events', 'result', 'cancel', 'approve', 'usage', 'caps', 'learned', 'meta', 'kill', 'forget'):"
if "'revise'" not in t:
    assert t.count(old) == 1, 'portal anchor'
    t2 = t.replace(old, "if cmd not in ('submit', 'list', 'status', 'events', 'result', 'cancel', 'approve', 'revise', 'usage', 'caps', 'learned', 'meta', 'kill', 'forget'):")
    old2 = "'client_id': str(body.get('client_id') or '')[:60],"
    assert t2.count(old2) == 1, 'portal anchor2'
    t2 = t2.replace(old2, "'client_id': str(body.get('client_id') or '')[:60], 'expected': body.get('expected') if isinstance(body.get('expected'), int) else None,")
    ast.parse(t2)
    qb = q.with_name(q.name + '.bak-vor-revise-20261028')
    if not qb.exists():
        shutil.copy2(q, qb)
    q.write_text(t2, encoding='utf-8')
    print('portal patched')
else:
    print('portal already patched')
