"""V10.1: two REAL Linux users. Program filters are not enough - the OS must stop person B
from reading person A's brain DB, vault index, queue and backups. Needs root + useradd
(skipped otherwise, e.g. on the developer's machine)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAN = os.name == 'posix' and hasattr(os, 'geteuid') and os.geteuid() == 0 and shutil.which('useradd') \
    and shutil.which('setpriv')
USERS = ('brain-test-a', 'brain-test-b')


def ensure_user(name):
    if subprocess.run(['id', name], capture_output=True).returncode != 0:
        subprocess.run(['useradd', '--system', '--no-create-home', '--shell', '/usr/sbin/nologin', name], check=True)
    return int(subprocess.run(['id', '-u', name], capture_output=True, text=True).stdout)


def as_user(uid, code, env=None):
    return subprocess.run(['setpriv', f'--reuid={uid}', f'--regid={uid}', '--clear-groups', sys.executable, '-c', code],
                          capture_output=True, text=True, timeout=60, env={'PATH': '/usr/bin:/bin', **(env or {})})


@unittest.skipUnless(CAN, 'needs root, useradd and setpriv')
class TwoRealUsers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.uid = {u: ensure_user(u) for u in USERS}
        cls.base = Path(tempfile.mkdtemp(prefix='brain-os-'))
        os.chmod(cls.base, 0o755)
        shutil.copytree(ROOT, cls.base / 'rt', ignore=shutil.ignore_patterns('__pycache__', 'tests'))
        os.chmod(cls.base / 'rt', 0o755)
        for d in (cls.base / 'rt').rglob('*'):
            os.chmod(d, 0o755 if d.is_dir() else 0o644)
        cls.home = {}
        for u in USERS:
            h = cls.base / u; h.mkdir(); os.chown(h, cls.uid[u], cls.uid[u]); os.chmod(h, 0o700)
            cls.home[u] = h
        a = cls.home['brain-test-a']
        code = (f"import sys;sys.path.insert(0,{str(cls.base / 'rt')!r})\n"
                "from brain_core import Brain\nfrom knowledge_index import VaultIndex\nfrom pathlib import Path\n"
                f"h=Path({str(a)!r}); (h/'vault').mkdir(); (h/'vault'/'n.md').write_text('# n\\nGeheim Alpha')\n"
                "b=Brain(h/'state'/'brain.db','person-a',{'ma-home'}); r=b.propose('ma-home','t','Geheim Alpha','s'); b.confirm(r['id'])\n"
                "v=VaultIndex(h/'state'/'idx.db',h/'vault'); v.build(); print(len(v.search('Geheim')['items']))")
        r = as_user(cls.uid['brain-test-a'], code)
        assert r.returncode == 0 and r.stdout.strip() == '1', r.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base, ignore_errors=True)

    def b_tries(self, code):
        return as_user(self.uid['brain-test-b'], f"import sys;sys.path.insert(0,{str(self.base / 'rt')!r})\n" + code)

    def test_b_cannot_open_a_brain_db_or_index(self):
        a = self.home['brain-test-a']
        for path in (a / 'state' / 'brain.db', a / 'state' / 'idx.db', a / 'vault' / 'n.md'):
            r = self.b_tries(f"open({str(path)!r},'rb').read(); print('LEAK')")
            self.assertNotIn('LEAK', r.stdout); self.assertIn('PermissionError', r.stderr)

    def test_b_with_a_paths_in_its_own_config_fails(self):
        a = self.home['brain-test-a']
        r = self.b_tries("from brain_core import Brain\n"
                         f"Brain({str(a / 'state' / 'brain.db')!r},'person-b',{{'ma-home'}}).recall('ma-home','Geheim Alpha')\n"
                         "print('LEAK')")
        self.assertNotIn('LEAK', r.stdout); self.assertNotEqual(r.returncode, 0)

    def test_files_created_by_a_are_owner_only(self):
        a = self.home['brain-test-a']
        for f in (a / 'state' / 'brain.db', a / 'state' / 'idx.db'):
            st = f.stat()
            self.assertEqual((st.st_uid, st.st_mode & 0o077), (self.uid['brain-test-a'], 0), f)

    def test_b_own_brain_is_separate(self):
        h = self.home['brain-test-b']
        r = self.b_tries("from brain_core import Brain\nfrom pathlib import Path\n"
                         f"b=Brain(Path({str(h)!r})/'brain.db','person-b',{{'ma-home'}})\n"
                         "print(len(b.recall('ma-home','Geheim Alpha')['items']))")
        self.assertEqual(r.stdout.strip(), '0', r.stderr)


if __name__ == '__main__':
    unittest.main()
