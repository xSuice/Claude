"""S-01: host_config() must keep operator-added extra_uids/extra_gid in /etc/ma-home/host.json.
Idempotent; backup; syntax check; behaviour test in a temp dir (no production write)."""
import py_compile,shutil,sys,json,tempfile,types,os
P='/opt/ma-home/manage.py'
s=open(P).read()
OLD="def host_config(st):\n    atomic(ETC / 'host.json',dict(users=st['users'],web_uid=st['ma-web_uid'],web_gid=st['ma-web_gid'],converter_image=st['converter_image'],printer_ready=st.get('printer_ready',False),scanner=st.get('scanner','')))\n"
NEW="""def host_config(st):
    # KEEP-EXTRA-UIDS: operator-added portal->agent access (extra_uids/extra_gid) must survive re-provisioning.
    cfg=dict(users=st['users'],web_uid=st['ma-web_uid'],web_gid=st['ma-web_gid'],converter_image=st['converter_image'],printer_ready=st.get('printer_ready',False),scanner=st.get('scanner',''))
    try:
        old=json.loads((ETC / 'host.json').read_text())
        for key in ('extra_uids','extra_gid'):
            if key in old:cfg[key]=old[key]
    except (OSError,ValueError):pass
    atomic(ETC / 'host.json',cfg)
"""
if 'KEEP-EXTRA-UIDS' in s:
    print('already present');sys.exit(0)
assert s.count(OLD)==1,'anchor'
# behaviour test on the NEW function text in isolation
ns={'json':json,'ETC':None,'atomic':None}
d=tempfile.mkdtemp()
from pathlib import Path
ns['ETC']=Path(d)
def atomic(path,obj):
    Path(path).write_text(json.dumps(obj))
ns['atomic']=atomic
exec(NEW,ns)
st={'users':{},'ma-web_uid':999,'ma-web_gid':981,'converter_image':'x'}
(Path(d)/'host.json').write_text(json.dumps({'extra_uids':[1000],'extra_gid':1000,'junk':1}))
ns['host_config'](st);r=json.loads((Path(d)/'host.json').read_text())
assert r['extra_uids']==[1000] and r['extra_gid']==1000 and 'junk' not in r,r
os.unlink(Path(d)/'host.json');ns['host_config'](st);r=json.loads((Path(d)/'host.json').read_text())
assert 'extra_uids' not in r,r
(Path(d)/'host.json').write_text('{broken');ns['host_config'](st);assert 'extra_uids' not in json.loads((Path(d)/'host.json').read_text())
print('isolated behaviour test OK (keep / absent / corrupt)')
shutil.copy(P,P+'.bak-vor-keepextra-20261027')
open(P,'w').write(s.replace(OLD,NEW))
py_compile.compile(P,doraise=True)
print('patched')
