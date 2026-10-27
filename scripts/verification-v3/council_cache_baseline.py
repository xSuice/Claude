"""Read-only aggregate of existing specialist session metrics. No prompts, tool arguments or identities exported.
Counters are lifetime values of persisted sessions, NOT 24h billing. DM tool completions are NOT council rounds.
"""
import collections,json,os,pathlib,sqlite3,time
root=pathlib.Path(os.environ['LOCALAPPDATA'])/'hermes/profiles'
rows=[];errors=[]
for home in sorted(root.glob('jarvis-*')):
 p=home/'state.db'
 if not p.exists():continue
 try:
  c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True,timeout=10)
  stats=c.execute('select count(*),coalesce(sum(input_tokens),0),coalesce(sum(output_tokens),0),coalesce(sum(cache_read_tokens),0),coalesce(sum(cache_write_tokens),0),coalesce(sum(api_call_count),0) from sessions').fetchone()
  msgs=c.execute('select id,tool_call_id,tool_call_uid,content from messages where role=? and tool_name=?',('tool','message_agent')).fetchall()
  dedup={};status=collections.Counter()
  for mid,cid,uid,content in msgs:
   key=uid or cid or 'row:'+str(mid)
   if key in dedup:continue
   dedup[key]=True
   try:d=json.loads(content or '{}')
   except (ValueError,TypeError):d={}
   status[str(d.get('status') or ('error' if d.get('error') else 'unknown'))]+=1
  rows.append({'profile':home.name,'sessions':stats[0],'input_tokens_lifetime':stats[1],'output_tokens_lifetime':stats[2],'cache_read_tokens_lifetime':stats[3],'cache_write_tokens_lifetime':stats[4],'api_call_count_lifetime':stats[5],'dm_completion_records':len(dedup),'dm_completion_statuses':dict(status)})
  c.close()
 except Exception as e:errors.append({'profile':home.name,'error':type(e).__name__})
report={'observed_unix':time.time(),'scope':'Lifetime persisted-session counters. No inferred cost/savings; DM completion counts do NOT establish council rounds or delivery. Read-only original DBs.','profiles':rows,'errors':errors}
p=pathlib.Path('C:/Users/andre/Documents/kimi-solo-dev/V3-COUNCIL-CACHE-BASELINE.json');p.write_text(json.dumps(report,indent=2),encoding='utf-8')
keys=['sessions','input_tokens_lifetime','output_tokens_lifetime','cache_read_tokens_lifetime','cache_write_tokens_lifetime','api_call_count_lifetime','dm_completion_records']
print(json.dumps({'profiles':len(rows),'totals':{k:sum(r[k] for r in rows) for k in keys},'errors':errors},indent=2))
