import tempfile
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from brain_core import Brain
from observer import inspect

class SensorTests(unittest.TestCase):
    def test_only_parser_no_execution_and_changed_file_event(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'project';root.mkdir()
            marker=Path(d)/'should-not-exist'
            (root/'bad.py').write_text(f"open({str(marker)!r},'w').write('oops')\ndef broken(:\n")
            (root/'broken.json').write_text('{"bad":}')
            (root/'.env').write_text('SECRET=hidden')
            out=inspect(root)
            self.assertEqual(out['invalid'],2)
            self.assertFalse(marker.exists())
            self.assertTrue(all('.env' not in str(x) for x in out['errors']))
            brain=Brain(Path(d)/'state.sqlite','u',{'work'})
            self.assertTrue(brain.record_observation('work',out)['logged'])
            self.assertFalse(brain.record_observation('work',out)['logged'])
            self.assertEqual(len(brain.insights('work')['episodes']),1)
            (root/'bad.py').write_text('ok=1\n')
            changed=inspect(root)
            self.assertNotEqual(changed['digest'],out['digest'])
            self.assertTrue(brain.record_observation('work',changed)['logged'])
    def test_not_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'in';root.mkdir()
            other=Path(d)/'outside.py';other.write_text('syntax bad(\n')
            (root/'outside.py').symlink_to(other)
            self.assertEqual(inspect(root)['checked'],0)
