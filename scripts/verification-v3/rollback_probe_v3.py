"""Exercise existing cutover rollback, then always restore the current portal.
No database/config/UI-data changes. Run as root; refuse when jobs are busy.
"""
import hashlib,json,os,pathlib,shutil,subprocess,time,urllib.request,urllib.error
P=pathlib.Path('/opt/ma-home/portal.py')
C=json.loads(pathlib.Path('/etc/ma-home/portal.json').read_text())
headers={'X-MA-Key':C['proxy_key'],'Remote-User':'andrew'}
def get(path,auth=True):
 r=urllib.request.Request('http://127.0.0.1:18765'+path,headers=headers if auth else {})
 try:
  with urllib.request.urlopen(r,timeout=20) as f:return f.status,f.read().decode()
 except urllib.error.HTTPError as e:return e.code,e.read().decode()
def wait():
 for _ in range(40):
  try:
   if get('/healthz',False)[0]==200:return
  except OSError:pass
  time.sleep(.5)
 raise RuntimeError('health timeout')
status=json.loads(get('/api/status')[1]); agents=json.loads(get('/api/jarvis/agents')[1])
assert status.get('busy') is False, 'document jobs busy or unknown'
assert agents.get('engine',{}).get('active')==[], 'engine jobs active or unknown'
raw=P.read_bytes(); st=P.stat(); backup=P.with_name(P.name+'.bak-vor-rollback-probe')
shutil.copy2(P,backup)
result={'started':time.time(),'initial_sha256':hashlib.sha256(raw).hexdigest(),'backup':str(backup),'tests':{}}
try:
 subprocess.run(['bash','/opt/ma-home/rollback-cutover.sh'],check=True,timeout=45,capture_output=True,text=True)
 wait();code,body=get('/')
 assert code==200 and '<title>MA Home</title>' in body, 'classic rollback root incorrect'
 result['tests']['classic_root']=True
 assert get('/',False)[0]==401,'rollback auth gate failed'
 result['tests']['classic_auth']=True
finally:
 temp=P.with_name(P.name+'.restore-probe')
 temp.write_bytes(raw);os.chmod(temp,st.st_mode & 0o777);os.chown(temp,st.st_uid,st.st_gid);os.replace(temp,P)
 subprocess.run(['systemctl','restart','ma-home-web'],check=True,timeout=30)
 wait();code,body=get('/')
 result['tests']['hq_restored']=code==200 and '<title>MA-HOME HQ</title>' in body
 result['tests']['auth_restored']=get('/',False)[0]==401
 result['tests']['source_identical']=hashlib.sha256(P.read_bytes()).hexdigest()==result['initial_sha256']
 result['tests']['bundle_served']=get('/staging/js/app.bundle.js')[0]==200
 result['finished']=time.time()
 pathlib.Path('/tmp/v3-rollback-probe.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(result,indent=2))
 assert all(result['tests'].values()),'restoration verification failed'
assert result['tests'].get('classic_root') and result['tests'].get('classic_auth')
