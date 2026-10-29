"""Run on server, exercises the real network-isolated candidate, no model calls."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

class BoundaryTests(unittest.TestCase):
    def test_live_network_boundary(self):
        runner = Path(__file__).with_name('network_runner.py')
        self.assertTrue(runner.exists(), 'network-isolated runner missing')
        work = Path.home() / 'hermes-qualification/jobs/network-test'
        work.mkdir(parents=True, exist_ok=True)
        probe = '''import socket,json,urllib.request
r={}
for host,port in [('127.0.0.1',18765),('192.168.0.111',22),('1.1.1.1',443)]:
    try:
        s=socket.create_connection((host,port),timeout=1);s.close();r[host]='REACHABLE'
    except OSError:r[host]='blocked'
for path in ['/run/ma-home/agent.sock','/run/ma-claude/bridge.sock','/run/user/1000/bus','/run/docker.sock']:
    try:
        s=socket.socket(socket.AF_UNIX);s.settimeout(1);s.connect(path);s.close();r[path]='REACHABLE'
    except OSError:r[path]='blocked'
for host in ['dialagram.me','api.kimi.ai','example.com']:
    try:
        with urllib.request.urlopen('https://'+host+'/',timeout=20) as response:r[host]=response.status
    except urllib.error.HTTPError as e:r[host]=e.code
    except OSError:r[host]='blocked'
print(json.dumps(r))
'''
        p = subprocess.run([sys.executable, str(runner), str(work), '--', '/usr/bin/python3', '-c', probe], capture_output=True, text=True, timeout=90)
        self.assertEqual(p.returncode, 0, p.stderr)
        r = json.loads(p.stdout)
        for key in ['127.0.0.1','192.168.0.111','1.1.1.1','/run/ma-home/agent.sock','/run/ma-claude/bridge.sock','/run/user/1000/bus','/run/docker.sock','example.com']:
            self.assertEqual(r[key], 'blocked', (key,r))
        for host in ['dialagram.me','api.kimi.ai']:
            self.assertIsInstance(r[host], int, r)
        print(json.dumps(r, sort_keys=True))

    def test_runner_timeout_env_and_no_timeout_for_terminal(self):
        import pty
        runner = Path(__file__).with_name('network_runner.py')
        work = Path.home() / 'hermes-qualification/jobs/timeout-test'
        work.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, MA_RUNNER_TIMEOUT='2')
        cmd = [sys.executable, str(runner), str(work), '--', '/bin/sleep', '4']
        p = subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
        self.assertEqual(p.returncode, 124)                      # Hintergrundauftrag: hartes Limit
        master, slave = pty.openpty()
        p = subprocess.run(cmd, env=env, stdin=slave, capture_output=True, timeout=30)
        os.close(master); os.close(slave)
        self.assertEqual(p.returncode, 0)                        # interaktive Sitzung am Terminal: kein Limit

    def test_cancel_kills_detached_descendants(self):
        import os
        import signal
        import time
        import uuid
        marker = 'hermes-lifecycle-' + uuid.uuid4().hex
        work = Path.home() / 'hermes-qualification/jobs/lifecycle-test'
        work.mkdir(parents=True, exist_ok=True)
        ready = work / 'ready'
        ready.unlink(missing_ok=True)
        code = "import subprocess,time,pathlib; subprocess.Popen(['/usr/bin/python3','-c','import time; time.sleep(120)'," + repr(marker) + "],start_new_session=True); pathlib.Path(" + repr(str(ready)) + ").write_text('ready'); time.sleep(120)"
        command = [sys.executable, str(Path(__file__).with_name('network_runner.py')), str(work), '--', '/usr/bin/python3', '-c', code]
        p = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            for _ in range(100):
                if ready.exists() or p.poll() is not None:
                    break
                time.sleep(.1)
            self.assertTrue(ready.exists(), 'sandbox did not start')
            p.terminate()
            p.wait(timeout=10)
            time.sleep(.5)
            survivors = []
            for entry in Path('/proc').iterdir():
                if not entry.name.isdigit():
                    continue
                try:
                    if marker.encode() in (entry / 'cmdline').read_bytes():
                        survivors.append(entry.name)
                except OSError:
                    pass
            self.assertEqual(survivors, [], 'detached child survived cancellation')
        finally:
            if p.poll() is None:
                p.kill()
                p.wait()
            p.stderr.close()

if __name__ == '__main__':
    unittest.main()
