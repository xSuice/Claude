"""SEC-001: rotate the portal proxy key (X-MA-Key) in portal.json, Caddyfile and state.json (manage.py source).
Backups *.bak-vor-keyrotation-20261027 (same mode/owner). Never prints a key. Run with sudo, then restart caddy container."""
import json, os, secrets, shutil
from pathlib import Path

TAG = '.bak-vor-keyrotation-20261027'
PJ, CF, SJ = Path('/etc/ma-home/portal.json'), Path('/etc/ma-home/Caddyfile'), Path('/etc/ma-home/state.json')
old = json.loads(PJ.read_text())['proxy_key']
st = json.loads(SJ.read_text())
assert st.get('proxy_key') == old, 'state.json key differs'
assert CF.read_text().count(old) == 1, 'Caddyfile key count'
new = secrets.token_hex(32)
assert new != old and len(new) == 64


def write(p, text):
    b = p.with_name(p.name + TAG)
    if not b.exists():
        shutil.copy2(p, b)
    s = p.stat()
    tmp = p.with_name(p.name + '.tmp-rot')
    tmp.write_text(text)
    os.chown(tmp, s.st_uid, s.st_gid)
    os.chmod(tmp, s.st_mode & 0o7777)
    os.replace(tmp, p)


pj = json.loads(PJ.read_text()); pj['proxy_key'] = new
st['proxy_key'] = new
write(SJ, json.dumps(st, ensure_ascii=False, indent=2))
write(PJ, json.dumps(pj, ensure_ascii=False, indent=2))
write(CF, CF.read_text().replace(old, new))
ok = json.loads(PJ.read_text())['proxy_key'] == new and json.loads(SJ.read_text())['proxy_key'] == new and CF.read_text().count(new) == 1 and old not in CF.read_text()
print('rotated' if ok else 'MISMATCH', 'fingerprint', __import__('hashlib').sha256(new.encode()).hexdigest()[:8])
