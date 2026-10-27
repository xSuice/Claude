"""Rotate the nexum API key across all places WITHOUT the key ever passing through chat or command lines.

Usage (in your own terminal):
    python rotate_nexum.py --dry-run                      # list targets, no changes
    python rotate_nexum.py --new-key-file C:/path/new.key # applies; prompts nothing, prints only fingerprints
    (without --new-key-file in --apply mode the key is read hidden from the keyboard via getpass)

Targets: 18 profile .env files (NEXUM_API_KEY=...) + ma-server ~/.config/ma-jarvis/keys/nexum.key.
Safety: backups of every file (<name>.bak-vor-nexum-rotation), atomic replace, per-target fingerprint read-back,
the old key is NOT revoked here (do that at the provider after the read-back is green). The new-key file is wiped after success if --wipe is given.
"""
import argparse,getpass,glob,hashlib,os,re,shutil,subprocess,sys,tempfile
TEST=os.environ.get('ROTATE_TEST_ROOT')  # tests only: temp root, remote part simulated
ROOT=TEST or os.path.join(os.environ['LOCALAPPDATA'],'hermes')
SSH=['ssh','-i',os.path.expanduser('~/.ssh/hermes_mahome'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','andrew@ma-server']
REMOTE='~/.config/ma-jarvis/keys/nexum.key'
fp=lambda s:hashlib.sha256(s.strip().encode()).hexdigest()[:12]
LINE=re.compile(r'^(\s*NEXUM_API_KEY\s*=\s*)(.*)$')

def env_files():
    return sorted(glob.glob(os.path.join(ROOT,'profiles','*','.env')))

def current_in_env(p):
    for l in open(p,encoding='utf-8',errors='replace'):
        m=LINE.match(l.rstrip('\r\n'))
        if m:return m.group(2).strip().strip('\'"')
    return None

def remote_current():
    if TEST:return open(os.path.join(TEST,'server.key')).read().strip()
    r=subprocess.run(SSH+['cat '+REMOTE],capture_output=True,text=True,timeout=30)
    return r.stdout.strip() if r.returncode==0 else None

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dry-run',action='store_true');ap.add_argument('--new-key-file');ap.add_argument('--wipe',action='store_true')
    a=ap.parse_args()
    allf=env_files();files=[f for f in allf if current_in_env(f) is not None];srv=remote_current()
    print('skipped (no NEXUM_API_KEY line):',[os.path.basename(os.path.dirname(f)) for f in allf if f not in files])
    print('targets: %d .env files + server key file (%s)'%(len(files),'readable' if srv else 'NOT readable'))
    cur={os.path.basename(os.path.dirname(p)):current_in_env(p) for p in files}
    same={k:(v==srv) for k,v in cur.items()}
    print('currently identical to server key:',sum(same.values()),'of',len(same),'| missing line:',[k for k,v in cur.items() if v is None])
    if a.dry_run:return 0
    if a.new_key_file:new=open(a.new_key_file,encoding='utf-8').read().strip()
    else:new=getpass.getpass('Neuer nexum-Schluessel (unsichtbar): ').strip()
    if len(new)<20 or re.search(r'\s',new):sys.exit('abort: key format implausible')
    if new==srv:sys.exit('abort: new key equals current key')
    print('new key fingerprint:',fp(new),'len',len(new))
    # 1) backups
    for p in files:shutil.copy2(p,p+'.bak-vor-nexum-rotation')
    # 2) PC .env files (atomic)
    done=[]
    try:
        for p in files:
            text=open(p,encoding='utf-8',errors='replace').read().splitlines(keepends=True);out=[];hit=0
            for l in text:
                m=LINE.match(l.rstrip('\r\n'))
                if m:out.append(m.group(1)+new+('\r\n' if l.endswith('\r\n') else '\n'));hit+=1
                else:out.append(l)
            if hit!=1:raise RuntimeError('unexpected NEXUM_API_KEY count %d in %s'%(hit,os.path.basename(os.path.dirname(p))))
            fd,tmp=tempfile.mkstemp(dir=os.path.dirname(p),prefix='.env-');os.close(fd)
            open(tmp,'w',encoding='utf-8',newline='').write(''.join(out));os.replace(tmp,p);done.append(p)
        # 3) server key file via stdin (not in command line)
        if TEST:open(os.path.join(TEST,'server.key'),'w').write(new);r=type('R',(),{'returncode':0})()
        else:r=subprocess.run(SSH+['umask 077; cp %s %s.bak-vor-nexum-rotation && cat > %s.new && chmod 600 %s.new && mv %s.new %s'%((REMOTE,)*1+(REMOTE,)*5)],input=new,capture_output=True,text=True,timeout=40)
        if r.returncode:raise RuntimeError('server write failed')
    except Exception as e:
        print('ERROR -> restoring PC files from backups:',e)
        for p in done:shutil.copy2(p+'.bak-vor-nexum-rotation',p)
        sys.exit(1)
    # 4) read-back
    bad=[k for k,p in ((os.path.basename(os.path.dirname(p)),p) for p in files) if current_in_env(p)!=new]
    if remote_current()!=new:bad.append('server')
    print('read-back: %d/%d targets match fingerprint %s'%(len(files)+1-len(bad),len(files)+1,fp(new)),'| mismatches:',bad)
    if not bad and a.wipe and a.new_key_file:
        open(a.new_key_file,'w').write('x'*len(new));os.remove(a.new_key_file);print('key file wiped')
    print('NEXT: new Hermes sessions pick the key up; restart gateway (hermes gateway restart) to be sure; then revoke the OLD key at the provider.')
    return 1 if bad else 0
if __name__=='__main__':sys.exit(main())
