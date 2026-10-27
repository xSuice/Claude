import glob,os,subprocess
root=os.path.join(os.environ['LOCALAPPDATA'],'hermes')
srv=subprocess.run(['ssh','-i',os.path.expanduser('~/.ssh/hermes_mahome'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','andrew@ma-server','cat ~/.config/ma-jarvis/keys/nexum.key'],capture_output=True,text=True,timeout=30).stdout.strip().encode()
assert len(srv)>20
import glob
hits={}
cands=glob.glob(os.path.join(root,'profiles','*','.env'))+glob.glob(os.path.join(root,'profiles','*','config.yaml'))+glob.glob(os.path.join(root,'profiles','*','sessions','request_dump_*.json'))+glob.glob(os.path.join(root,'profiles','*','logs','*.log'))+glob.glob(os.path.join(root,'profiles','*','logs','process-results','*.json'))+glob.glob(os.path.join(root,'.env'))
for p in cands:
    try:
        if os.path.getsize(p)>8_000_000:continue
        if srv in open(p,'rb').read():
            k=(os.path.basename(os.path.dirname(os.path.dirname(p))) if 'sessions' in p or 'logs' in p else os.path.basename(os.path.dirname(p)), 'dump' if 'request_dump' in p else 'process-result' if 'process-results' in p else 'log' if p.endswith('.log') else os.path.basename(p))
            hits[k]=hits.get(k,0)+1
    except OSError:pass
print('scanned',len(cands),'files')
by={}
for (prof,kind),n in hits.items():by[kind]=by.get(kind,0)+n
print('files containing the key by kind:',by)
print('profiles with key in non-.env files:',sorted({pr for (pr,kind) in hits if kind not in ('.env',)}))
