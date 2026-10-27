"""Council DM-chain metrics, metadata only (sender, target, timestamp). No message text is read into output.
Chain = consecutive DMs between the same unordered agent pair with gaps <= GAP seconds.
This measures observed message_agent calls in persisted profile sessions; it does NOT prove delivery, topic, or quality.
A 'round' is not directly observable; chain length (directed messages) is reported against the SOUL budget of 3 rounds (~6 messages)."""
import collections,json,os,pathlib,sqlite3,statistics,time
GAP=1800
root=pathlib.Path(os.environ['LOCALAPPDATA'])/'hermes/profiles'
events={}
for home in sorted(root.glob('jarvis-*')):
    p=home/'state.db'
    if not p.exists():continue
    c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True,timeout=10)
    for mid,ts,tcs in c.execute("select id,timestamp,tool_calls from messages where role='assistant' and tool_calls like '%message_agent%'"):
        try:calls=json.loads(tcs)
        except Exception:continue
        for call in calls:
            f=call.get('function',{})
            if f.get('name')!='message_agent':continue
            try:tgt=str(json.loads(f.get('arguments') or '{}').get('target','')).lstrip('@')
            except Exception:continue
            key=(home.name,call.get('id') or ('row',mid))
            events[key]=(float(ts),home.name,tgt)
    c.close()
ev=sorted(events.values())
chains=[];open_={}
for ts,src,tgt in ev:
    pair=tuple(sorted((src,tgt)))
    ch=open_.get(pair)
    if ch and ts-ch['last']<=GAP:
        ch['n']+=1;ch['last']=ts
    else:
        ch={'pair':pair,'n':1,'first':ts,'last':ts};open_[pair]=ch;chains.append(ch)
ns=[c['n'] for c in chains]
by_day=collections.Counter(time.strftime('%Y-%m-%d',time.localtime(t)) for t,_,_ in ev)
top=sorted(chains,key=lambda c:-c['n'])[:10]
cut=time.mktime((2026,10,26,0,0,0,0,0,-1))
def split(sel):
    n=[c['n'] for c in sel]
    return {'chains':len(sel),'directed_dms':sum(n),'max':max(n) if n else None,'over_6':sum(x>6 for x in n),'over_12':sum(x>12 for x in n)}
rep={'split_note':'Chains starting before/after 2026-10-26 (A4-1 tool lockdown + A4-2 debate budget introduced 26.10.). Correlation, not proof of causation.','before_2026-10-26':split([c for c in chains if c['first']<cut]),'from_2026-10-26':split([c for c in chains if c['first']>=cut]),'scope':__doc__,'observed':time.time(),'directed_dm_calls':len(ev),'chains':len(chains),
 'chain_len':{'median':statistics.median(ns) if ns else None,'max':max(ns) if ns else None,'over_6':sum(n>6 for n in ns),'over_12':sum(n>12 for n in ns)},
 'per_day':dict(sorted(by_day.items())),
 'longest':[{'pair':list(c['pair']),'messages':c['n'],'duration_min':round((c['last']-c['first'])/60,1),'start':time.strftime('%Y-%m-%d %H:%M',time.localtime(c['first']))} for c in top]}
pathlib.Path('C:/Users/andre/Documents/kimi-solo-dev/V3-COUNCIL-CHAINS.json').write_text(json.dumps(rep,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:v for k,v in rep.items() if k!='scope'},indent=1,ensure_ascii=False))
