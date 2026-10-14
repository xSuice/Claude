import json
import tempfile
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from diagnose_claude import analyze

class Diagnosis(unittest.TestCase):
    def test_double_hook_detected_without_command_disclosure(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'.claude').mkdir()
            s={'hooks':{'PostToolUse':[{'matcher':'Bash','hooks':[{'type':'command','command':'SECRET=abc python run.py'}]}]}}
            (root/'.claude'/'settings.json').write_text(json.dumps(s))
            (root/'.claude'/'settings.local.json').write_text(json.dumps(s))
            out=analyze(root)
            self.assertEqual(out['duplicate_hook_entries'],1)
            self.assertNotIn('SECRET=abc',json.dumps(out))
    def test_clean_project(self):
        with tempfile.TemporaryDirectory() as d:
            out=analyze(Path(d))
            self.assertEqual(out['duplicate_hook_entries'],0)
