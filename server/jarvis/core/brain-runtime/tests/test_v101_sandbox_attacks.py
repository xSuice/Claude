"""V10.1: deliberately hostile (but harmless) programs against the sandbox. Each tries one
escape; the test fails if it succeeds. Written before the hardening."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import runner
import sandbox

PY = sys.executable


@unittest.skipUnless(sandbox.available(), 'namespaces not available')
class SandboxAttacks(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.dir = Path(t.name); self.work = self.dir / 'work'; self.work.mkdir()
        self.secret_dir = self.dir / 'state'; self.secret_dir.mkdir()
        (self.secret_dir / 'key').write_text('TOPSECRET')

    def run_probe(self, code, env_secret=False):
        if env_secret:
            os.environ['BRAIN_TEST_SECRET'] = 'ENVSECRET123'
            self.addCleanup(os.environ.pop, 'BRAIN_TEST_SECRET', None)
        prelude = ("import ctypes, os, sys\nlibc = ctypes.CDLL(None, use_errno=True)\n"
                   f"SECRET = {str(self.secret_dir / 'key')!r}\nOUTSIDE = {str(self.dir / 'pwned')!r}\n")
        r = runner.run({'argv': [PY, '-c', prelude + code], 'cwd': '.', 'timeout': 20}, self.work,
                       {'hide': [str(self.secret_dir)]})
        return r['tail'].strip()

    def test_cannot_unmount_hiding_tmpfs(self):
        out = self.run_probe(
            "libc.umount2(os.path.dirname(SECRET).encode(), 2)\n"
            "try:\n print('LEAK' if open(SECRET).read()=='TOPSECRET' else 'clean')\nexcept OSError: print('clean')")
        self.assertEqual(out, 'clean')

    def test_own_namespaces_do_not_unlock_mounts(self):
        out = self.run_probe(
            "r=libc.unshare(0x10000000|0x00020000)\n"
            "if r==0:\n open('/proc/self/setgroups','w').write('deny'); open('/proc/self/uid_map','w').write('0 1000 1')\n"
            "libc.umount2(os.path.dirname(SECRET).encode(), 2)\n"
            "try:\n print('LEAK' if open(SECRET).read()=='TOPSECRET' else 'clean')\nexcept OSError: print('clean')")
        self.assertEqual(out.splitlines()[-1], 'clean')

    def test_cannot_remount_filesystem_writable(self):
        out = self.run_probe(
            "class A(ctypes.Structure):\n _fields_=[('s',ctypes.c_uint64),('c',ctypes.c_uint64),('p',ctypes.c_uint64),('u',ctypes.c_uint64)]\n"
            "a=A(0,1,0,0); libc.syscall(442,-100,b'/',0x8000,ctypes.byref(a),ctypes.sizeof(a))\n"
            "libc.mount(None, b'/', None, 32|4096, None)\n"
            "try:\n open(OUTSIDE,'w').write('x'); print('LEAK')\nexcept OSError: print('clean')")
        self.assertEqual(out, 'clean'); self.assertFalse((self.dir / 'pwned').exists())

    def test_cannot_read_host_process_environment(self):
        out = self.run_probe(
            "hits=[]\nfor p in os.listdir('/proc'):\n if p.isdigit():\n  try:\n"
            "   if b'ENVSECRET123' in open(f'/proc/{p}/environ','rb').read(): hits.append(p)\n  except OSError: pass\n"
            "print('LEAK' if hits else 'clean', len([p for p in os.listdir('/proc') if p.isdigit()]))", env_secret=True)
        self.assertTrue(out.startswith('clean'), out)
        self.assertLessEqual(int(out.split()[1]), 3)  # only its own PID namespace is visible

    def test_no_capabilities_and_no_new_privileges(self):
        out = self.run_probe(
            "st=dict(l.split(':',1) for l in open('/proc/self/status') if ':' in l)\n"
            "print(st['CapEff'].strip(), st['NoNewPrivs'].strip())")
        cap, nnp = out.split()
        self.assertEqual(int(cap, 16), 0, out); self.assertEqual(nnp, '1')

    def test_cannot_mount_new_tmpfs_or_proc(self):
        out = self.run_probe(
            "r1=libc.mount(b'tmpfs', b'/tmp', b'tmpfs', 0, None)\n"
            "r2=libc.mount(b'none', os.path.dirname(SECRET).encode(), None, 4096, None)\n"
            "print('clean' if r1!=0 and r2!=0 else 'LEAK')")
        self.assertEqual(out, 'clean')

    def test_work_dir_equal_to_hidden_path_stays_visible(self):
        (self.work / 'tests').mkdir()
        r = runner.run({'argv': [PY, '-c', "import os;print(os.path.isdir('tests'))"], 'cwd': '.'}, self.work,
                       {'hide': [str(self.work)]})
        self.assertEqual(r['tail'].strip(), 'True')

    def test_still_cannot_reach_network_or_write_outside(self):
        out = self.run_probe(
            "import socket\nres=[]\n"
            "try:\n socket.create_connection(('1.1.1.1',53),timeout=2); res.append('net')\nexcept OSError: pass\n"
            "try:\n open(OUTSIDE,'w'); res.append('write')\nexcept OSError: pass\n"
            "open('ok.txt','w').write('1')\nprint(','.join(res) or 'clean')")
        self.assertEqual(out, 'clean'); self.assertTrue((self.work / 'ok.txt').exists())


if __name__ == '__main__':
    unittest.main()
