"""Read-only telemetry helpers for the MA-HOME portal (no Flask import; unit-testable).
PC snapshot: strict numeric schema only (no process names/paths). Journal: counts + redacted, truncated error lines."""
import json,math,os,re,tempfile,time

STALE_S=180
UNIT_RE=re.compile(r'^[a-z0-9][a-z0-9@_.-]{0,60}$')
_REDACT=[
 (re.compile(r'(?i)\b(authorization)\s*[:=]\s*\S+(\s+\S+)?'),r'\1=[REDACTED]'),
 (re.compile(r'(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{6,}'),'Bearer [REDACTED]'),
 (re.compile(r'(?i)\b(x-ma-key|api[_-]?key|secret|password|passwd|token|pwd)\b\s*[:=]\s*"?[^\s",;]+"?'),r'\1=[REDACTED]'),
 (re.compile(r'\bsk-[A-Za-z0-9_-]{8,}'),'[REDACTED]'),
 (re.compile(r'(?<=//)[^/\s:@]+:[^/\s@]+@'),'[REDACTED]@'),
 (re.compile(r'\b[A-Fa-f0-9]{32,}\b'),'[REDACTED]'),
]
_CTRL=re.compile(r'\x1b\[[0-9;]*[A-Za-z]|[\x00-\x1f\x7f]')

def redact(text,limit=160):
    s=_CTRL.sub(' ',str(text))
    for rx,rep in _REDACT:s=rx.sub(rep,s)
    s=re.sub(r'\s+',' ',s).strip()
    return s if len(s)<=limit else s[:limit]+'…'

def _num(v,lo,hi,name):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or isinstance(v,float) and not math.isfinite(v) or not lo<=v<=hi:
        raise ValueError('invalid '+name)
    return float(v) if isinstance(v,float) else v

def validate_pc(d):
    if not isinstance(d,dict) or set(d)-{'cpu_pct','ram_pct','gpu'}:raise ValueError('unknown fields')
    out={'cpu_pct':_num(d.get('cpu_pct'),0,100,'cpu_pct'),'ram_pct':_num(d.get('ram_pct'),0,100,'ram_pct'),'gpu':None}
    g=d.get('gpu')
    if g is not None:
        keys={'util_pct':(0,100),'temp_c':(0,150),'vram_used_mb':(0,1e6),'vram_total_mb':(1,1e6)}
        if not isinstance(g,dict) or set(g)!=set(keys):raise ValueError('gpu fields')
        out['gpu']={k:_num(g[k],*keys[k],k) for k in keys}
        if out['gpu']['vram_used_mb']>out['gpu']['vram_total_mb']:raise ValueError('vram')
    return out

def write_pc(path,data,now=None):
    rec={'received':now if now is not None else time.time(),**data}
    d=os.path.dirname(path) or '.'
    fd,tmp=tempfile.mkstemp(dir=d,prefix='.pc-')
    try:
        with os.fdopen(fd,'w') as f:json.dump(rec,f)
        os.chmod(tmp,0o600);os.replace(tmp,path)
    except BaseException:
        try:os.unlink(tmp)
        except OSError:pass
        raise

def read_pc(path,now=None):
    now=now if now is not None else time.time()
    try:
        with open(path) as f:rec=json.load(f)
    except FileNotFoundError:return {'state':'missing'}
    except (ValueError,OSError):return {'state':'invalid'}
    try:
        age=now-float(rec['received']);v=validate_pc({k:rec.get(k) for k in ('cpu_pct','ram_pct','gpu')})
    except (KeyError,ValueError,TypeError):return {'state':'invalid'}
    return {'state':'fresh' if 0<=age<=STALE_S else 'stale','age_s':round(age),**v}

def safe_units(units):
    return [u for u in units if isinstance(u,str) and UNIT_RE.fullmatch(u)]

def summarize_journal(raw,keep=3):
    items=[]
    for line in raw.splitlines():
        try:j=json.loads(line);msg=j['MESSAGE'];ts=int(j['__REALTIME_TIMESTAMP'])//10**6
        except (ValueError,KeyError,TypeError):continue
        if isinstance(msg,str):items.append((ts,msg))
    items.sort(key=lambda x:-x[0])
    return {'errors':len(items),'last':[{'t':t,'msg':redact(m)} for t,m in items[:keep]]}
