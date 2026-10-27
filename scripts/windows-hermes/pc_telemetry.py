"""PC-side telemetry snapshot (strict schema, no process names / no message text). Used by liveness_reporter.py; failures never affect liveness."""
import json,os,shutil,sqlite3,subprocess,time

_council_cache={'t':0,'v':None}
WINDOW_H=24; GAP_S=1800; CACHE_S=600

def council_stats(now=None):
    """Counts message_agent calls in the last WINDOW_H hours from persisted profile sessions (metadata only: sender, target, time).
    Chain = consecutive DMs of the same unordered agent pair with gaps <= GAP_S. Returns None if nothing readable."""
    now=now or time.time()
    if _council_cache['v'] is not None and now-_council_cache['t']<CACHE_S:return _council_cache['v']
    root=os.path.join(os.environ.get('LOCALAPPDATA',''),'hermes','profiles')
    ev={}
    try:names=sorted(n for n in os.listdir(root) if n.startswith('jarvis-'))
    except OSError:return None
    cut=now-WINDOW_H*3600
    for n in names:
        p=os.path.join(root,n,'state.db')
        if not os.path.exists(p):continue
        try:
            c=sqlite3.connect('file:'+p.replace('\\','/')+'?mode=ro',uri=True,timeout=5)
            for mid,ts,tcs in c.execute("select id,timestamp,tool_calls from messages where role='assistant' and timestamp>=? and tool_calls like '%message_agent%'",(cut,)):
                try:calls=json.loads(tcs)
                except Exception:continue
                for call in calls:
                    f=call.get('function',{})
                    if f.get('name')!='message_agent':continue
                    try:tgt=str(json.loads(f.get('arguments') or '{}').get('target','')).lstrip('@')
                    except Exception:continue
                    ev[(n,call.get('id') or ('row',mid))]=(float(ts),n,tgt)
            c.close()
        except Exception:
            continue
    chains=[];open_={}
    for ts,src,tgt in sorted(ev.values()):
        pair=tuple(sorted((src,tgt)));ch=open_.get(pair)
        if ch and ts-ch['last']<=GAP_S:ch['n']+=1;ch['last']=ts
        else:
            ch={'n':1,'last':ts};open_[pair]=ch;chains.append(ch)
    ns=[c['n'] for c in chains]
    v={'window_h':WINDOW_H,'dms':len(ev),'chains':len(chains),'longest':max(ns) if ns else 0,'over_6':sum(x>6 for x in ns)}
    _council_cache.update(t=now,v=v);return v

def snapshot():
    import psutil
    d={'cpu_pct':round(psutil.cpu_percent(interval=0.5),1),'ram_pct':round(psutil.virtual_memory().percent,1),'gpu':None}
    exe=shutil.which('nvidia-smi')
    if exe:
        try:
            r=subprocess.run([exe,'--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=8,creationflags=0x08000000)
            u,t,mu,mt=[float(x) for x in r.stdout.strip().splitlines()[0].split(',')]
            d['gpu']={'util_pct':u,'temp_c':t,'vram_used_mb':mu,'vram_total_mb':mt}
        except Exception:
            d['gpu']=None
    try:
        cs=council_stats()
        if cs:d['council']=cs
    except Exception:
        pass
    return d

if __name__=='__main__':
    t=time.time();s=snapshot();print(json.dumps(s));print('seconds:',round(time.time()-t,1))
