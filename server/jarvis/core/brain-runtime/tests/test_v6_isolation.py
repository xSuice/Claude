import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class IsolatedInstall(unittest.TestCase):
    def test_new_install_creates_separate_database_references(self):
        import json
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            proc=subprocess.run(['python3',str(ROOT/'server/install_linux.py'),'--apply',
              '--isolate-profiles','--app-dir',str(d/'app'),'--data-dir',str(d/'data'),
              '--config-dir',str(d/'cfg')],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            a=json.loads((d/'cfg/person-a.json').read_text())
            b=json.loads((d/'cfg/person-b.json').read_text())
            self.assertNotEqual(a['state_db'],b['state_db'])
            self.assertTrue((d/'app/brain-runtime/autonomy.py').exists())
if __name__=='__main__':unittest.main()
