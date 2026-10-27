"""Compares nexum key fingerprints (SHA-256 prefix only; values never printed)."""
import hashlib,os,re,subprocess,sys,glob
def fp(s):return hashlib.sha256(s.strip().encode()).hexdigest()[:12]
root=os.path.join(os.environ['LOCALAPPDATA'],'hermes')
# server side
r=subprocess.run(['ssh','-i',os.path.expanduser('~/.ssh/hermes_mahome'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','andrew@ma-server','cat ~/.config/ma-jarvis/keys/nexum.key'],capture_output=True,text=True,timeout=30)
srv=r.stdout.strip();print('server key: len',len(srv),'fp',fp(srv) if srv else None)
# PC side: yaml lines near 'nexum'
seen={}
for cfg in glob.glob(os.path.join(root,'profiles','*','config.yaml'))+[os.path.join(root,'config.yaml')]:
    if not os.path.exists(cfg):continue
    lines=open(cfg,encoding='utf-8',errors='replace').read().splitlines()
    for i,l in enumerate(lines):
        if re.search(r'nexum',l,re.I):
            for j in range(max(0,i-6),min(len(lines),i+8)):
                m=re.match(r'\s*(api_key|key|api_key_env|key_env|token)\s*:\s*(.+?)\s*$',lines[j])
                if m:
                    k,v=m.group(1),m.group(2).strip('\'"')
                    kind='env-ref' if re.fullmatch(r'[A-Z][A-Z0-9_]{2,}',v) else 'literal'
                    seen.setdefault((os.path.basename(os.path.dirname(cfg)),k,kind,v if kind=='env-ref' else fp(v),len(v)),0)
for k in sorted(seen):print('PC',k)
# env files
for envf in glob.glob(os.path.join(root,'profiles','*','.env'))+[os.path.join(root,'.env')]:
    if not os.path.exists(envf):continue
    for l in open(envf,encoding='utf-8',errors='replace'):
        m=re.match(r'\s*([A-Z0-9_]*(?:NEXUM|DIALAGRAM)[A-Z0-9_]*)\s*=\s*(.*)$',l)
        if m:
            v=m.group(2).strip().strip('\'"');print('ENV',os.path.basename(os.path.dirname(envf)),m.group(1),'len',len(v),'fp',fp(v),'MATCH' if v==srv else 'DIFFERENT')
