"""Loopback Signal push. Never logs message bodies, account numbers or RPC errors."""
import json,urllib.request,re,time

def send(message,account,url='http://127.0.0.1:18769'):
 if not re.fullmatch(r'\+[1-9][0-9]{6,14}',account):raise ValueError('Invalid Signal account')
 data={'jsonrpc':'2.0','id':'jarvis-notify-'+str(time.time_ns()),'method':'send','params':{'account':account,'recipient':[account],'notifySelf':True,'message':'[JARVIS-MELDUNG] '+str(message['title'])+'\n'+str(message['message'])}}
 req=urllib.request.Request(url+'/api/v1/rpc',data=json.dumps(data).encode('utf-8'),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=60) as response:out=json.load(response)
 result=out.get('result') or {}
 if 'error' in out or not result.get('timestamp'):raise RuntimeError('Signal delivery failed')
 for item in result.get('results',[]):
  if item.get('type','SUCCESS')!='SUCCESS' or item.get('success') is False:raise RuntimeError('Signal delivery failed')
 return result['timestamp']
