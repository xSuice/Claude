import unittest,json
from unittest.mock import patch
import signal_push as S
class PushTests(unittest.TestCase):
 def test_signal_rpc_is_self_only_and_requests_push(self):
  class Response:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self):return b'{"jsonrpc":"2.0","result":{"timestamp":123}}'
  with patch.object(S.urllib.request,'urlopen',return_value=Response()) as call:
   self.assertEqual(S.send({'title':'Auftrag fertig','message':'Details im Portal'},'+491234567890'),123)
   req=call.call_args.args[0]; d=json.loads(req.data)
   self.assertEqual(d['method'],'send');self.assertEqual(d['params']['recipient'],['+491234567890'])
   self.assertTrue(d['params']['notifySelf']);self.assertNotIn('attachments',d['params'])
 def test_rpc_error_does_not_claim_success(self):
  class Response:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self):return b'{"error":{"message":"secret-canary"}}'
  with patch.object(S.urllib.request,'urlopen',return_value=Response()):
   with self.assertRaisesRegex(RuntimeError,'Signal delivery failed') as e:S.send({'title':'x','message':'y'},'+491234567890')
   self.assertNotIn('secret-canary',str(e.exception))
if __name__=='__main__':unittest.main()
