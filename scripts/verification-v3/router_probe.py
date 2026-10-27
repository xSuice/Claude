import json,subprocess,sys,time,uuid
KEY=subprocess.run(['ssh','-i',__import__('os').path.expanduser('~/.ssh/hermes_mahome'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','andrew@ma-server',"sudo python3 -c \"import json;print(json.load(open('/etc/ma-home/portal.json'))['proxy_key'])\""],capture_output=True,text=True,timeout=30).stdout.strip()
assert KEY
MODEL=sys.argv[2] if len(sys.argv)>2 else None
body=json.dumps({**({'model':MODEL} if MODEL else {}),'prompt':sys.argv[1],'session':'probe-'+uuid.uuid4().hex[:8],'dir':'notizen','mode':'lesen','files':[]})
script=f"""curl -sN --max-time 120 -X POST http://127.0.0.1:18765/api/claude -H 'X-MA-Key: {KEY}' -H 'Remote-User: andrew' -H 'Origin: https://ma-server.duckdns.org' -H 'X-MA-Request: 1' -H 'Content-Type: application/json' --data-binary @-"""
r=subprocess.run(['ssh','-i',__import__('os').path.expanduser('~/.ssh/hermes_mahome'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','andrew@ma-server',script],input=body,capture_output=True,text=True,timeout=150)
out=[]
for line in r.stdout.splitlines():
    try:d=json.loads(line)
    except ValueError:continue
    out.append(d)
res=[d for d in out if d.get('type')=='result']
bm=[d for d in out if d.get('type')=='bridge_model']
r0=res[-1] if res else {}
u=r0.get('usage',{})
print(json.dumps({'requested':MODEL,'bridge_model':bm[0] if bm else None,'result':r0.get('result'),'is_error':r0.get('is_error'),'cost_usd':r0.get('total_cost_usd'),'in':u.get('input_tokens'),'out':u.get('output_tokens'),'cache_create':u.get('cache_creation_input_tokens'),'cache_read':u.get('cache_read_input_tokens')}))
