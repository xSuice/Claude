import unittest, tempfile, pathlib, base64
import policy as P
class PolicyTests(unittest.TestCase):
 def test_only_self_sync_without_groups_is_admitted(self):
  own='+491234567890'
  self.assertTrue(P.is_owner_note({'envelope':{'sourceNumber':own,'syncMessage':{'sentMessage':{'destinationNumber':own,'message':'Hallo'}}}},own))
  self.assertFalse(P.is_owner_note({'envelope':{'sourceNumber':'+49999999999','dataMessage':{'message':'Hallo'}}},own))
  self.assertFalse(P.is_owner_note({'envelope':{'sourceNumber':own,'syncMessage':{'sentMessage':{'destinationNumber':own,'groupInfo':{'groupId':'group'}}}}},own))
 def test_paths_become_data_uri_without_mutating_input(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'voice.wav'; p.write_bytes(b'RIFFtest')
   original={'attachments':[str(p)],'message':'hello'}
   out=P.remote_params('send',original)
   self.assertEqual(original['attachments'],[str(p)])
   self.assertTrue(out['attachments'][0].startswith('data:audio/'))
   self.assertEqual(base64.b64decode(out['attachments'][0].split(',',1)[1]),b'RIFFtest')
 def test_missing_attachment_fails_before_network(self):
  with self.assertRaises(FileNotFoundError):P.remote_params('send',{'attachments':['nonexistent-voice-file.wav']})
 def test_direct_sends_notify_owner_phone_but_groups_and_other_rpcs_do_not(self):
  original={'recipient':['x'],'message':'Hallo'}
  self.assertTrue(P.remote_params('send',original)['notifySelf'])
  self.assertNotIn('notifySelf',original)
  self.assertNotIn('notifySelf',P.remote_params('send',{'groupId':'g','message':'x'}))
  self.assertNotIn('notifySelf',P.remote_params('sendTyping',{'recipient':['x']}))
if __name__=='__main__':unittest.main()
