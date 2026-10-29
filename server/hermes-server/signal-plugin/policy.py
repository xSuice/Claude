"""Self-chat admission and bounded cross-host attachments. No network or model calls."""
import base64,mimetypes
from pathlib import Path
MAX_ATTACHMENT=10*1024*1024

def is_owner_note(envelope,owner):
 e=envelope.get('envelope',envelope)
 s=e.get('syncMessage') or {}; sent=s.get('sentMessage') or {}
 source=e.get('sourceNumber') or e.get('source')
 dest=sent.get('destinationNumber') or sent.get('destination')
 return bool(owner and source==owner and dest==owner and not sent.get('groupInfo') and not str(sent.get('message','')).startswith('[JARVIS-MELDUNG]'))

def remote_params(method,params):
 out=dict(params)
 if method=='send' and 'groupId' not in params:out['notifySelf']=True
 if method!='send' or not params.get('attachments'):return out
 values=[]; total=0
 for filename in params['attachments']:
  p=Path(filename)
  with p.open('rb') as f:data=f.read(MAX_ATTACHMENT+1)
  total+=len(data)
  if total>MAX_ATTACHMENT:raise ValueError('Signal media limit: 10 MiB per send')
  mime=mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
  values.append('data:'+mime+';base64,'+base64.b64encode(data).decode('ascii'))
 out['attachments']=values
 return out
