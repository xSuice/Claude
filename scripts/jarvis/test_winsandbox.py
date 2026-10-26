"""Proof tests for winsandbox (Windows only): every isolation promise is checked with a counter-example.

    python -m unittest scripts/jarvis/test_winsandbox.py -v
JARVIS_SBX_NET=1 additionally checks that network=True really opens outbound internet (one HTTPS request to example.com).
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import winsandbox as w  # noqa: E402

WIN = os.name == 'nt'


@unittest.skipUnless(WIN, 'Windows only')
class Isolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sb = w.Sandbox()

    def setUp(self):
        self.work = w.new_workdir('test')
        self.addCleanup(w.cleanup, self.work)

    def run_sb(self, *argv, **lim):
        return self.sb.run(list(argv), self.work, w.Limits(**{'timeout_s': 60, **lim}))

    def test_runs_inside_an_appcontainer(self):
        r = self.run_sb('cmd', '/c', 'echo ok & whoami /groups')
        self.assertEqual(r.code, 0, r.output)
        self.assertIn('ok', r.output)
        self.assertIn('S-1-16-4096', r.output)  # AppContainer tokens run at low integrity

    def test_can_write_its_work_folder(self):
        r = self.run_sb('cmd', '/c', 'echo data> inside.txt')
        self.assertEqual(r.code, 0, r.output)
        self.assertEqual((self.work / 'inside.txt').read_text().strip(), 'data')

    def test_cannot_read_user_files(self):
        d = Path(tempfile.mkdtemp(prefix='jarvis-canary-'))  # user TEMP, not granted to the container
        self.addCleanup(shutil.rmtree, d, True)
        secret = f'CANARY-{uuid.uuid4().hex}'
        (d / 'secret.txt').write_text(secret)
        r = self.run_sb('cmd', '/c', f'type "{d / "secret.txt"}"')
        self.assertNotEqual(r.code, 0)
        self.assertNotIn(secret, r.output)
        r = self.run_sb('cmd', '/c', f'dir "{Path.home() / "Documents"}"')
        self.assertNotEqual(r.code, 0, 'Documents must not be listable')

    def test_cannot_write_outside(self):
        d = Path(tempfile.mkdtemp(prefix='jarvis-canary-'))
        self.addCleanup(shutil.rmtree, d, True)
        for target in (d / 'evil.txt', Path(os.environ['ProgramFiles']) / 'jarvis-evil.txt', Path.home() / 'jarvis-evil.txt'):
            r = self.run_sb('cmd', '/c', f'echo x> "{target}"')
            self.assertFalse(target.exists(), f'{target} was written')
            self.assertNotEqual(r.code, 0)

    def test_cannot_write_hkcu(self):
        key = r'HKCU\Software\MAJarvisSandboxTest'
        self.addCleanup(subprocess.run, ['reg', 'delete', key, '/f'], capture_output=True)
        r = self.run_sb('reg', 'add', key, '/v', 'x', '/d', '1', '/f')
        self.assertNotEqual(r.code, 0, r.output)
        self.assertNotEqual(subprocess.run(['reg', 'query', key], capture_output=True).returncode, 0, 'HKCU key exists')

    def test_no_network_by_default(self):
        curl = Path(os.environ['SystemRoot']) / 'System32' / 'curl.exe'
        if not curl.exists():
            self.skipTest('curl.exe fehlt')
        r = self.run_sb(str(curl), '-sS', '-m', '8', '-o', 'out.html', 'https://example.com/')
        self.assertIn(r.code, (6, 7, 28), f'outbound HTTPS must fail without internetClient: {r.output}')
        self.assertFalse((self.work / 'out.html').exists())
        r = self.run_sb(str(curl), '-sS', '-m', '5', '-o', 'out.html', 'http://127.0.0.1:8123/')
        self.assertNotEqual(r.code, 0, 'loopback (local services) must not be reachable')

    @unittest.skipUnless(os.environ.get('JARVIS_SBX_NET') == '1', 'set JARVIS_SBX_NET=1 for the positive network check')
    def test_network_only_with_capability(self):
        curl = str(Path(os.environ['SystemRoot']) / 'System32' / 'curl.exe')
        r = self.sb.run([curl, '-sS', '-m', '15', '-o', 'out.html', 'https://example.com/'], self.work,
                        w.Limits(timeout_s=60, network=True))
        self.assertEqual(r.code, 0, r.output)
        self.assertIn('Example Domain', (self.work / 'out.html').read_text(errors='replace'))

    def test_memory_cap_applies_to_the_tree(self):
        r = self.run_sb('java', '-Xms600m', '-Xmx600m', '-XX:+AlwaysPreTouch', '-version', mem_mb=256)
        self.assertNotEqual(r.code, 0, 'a JVM touching 600 MB must not run under a 256 MB job cap')
        r = self.run_sb('java', '-version', mem_mb=512)
        self.assertEqual(r.code, 0, r.output)

    def test_process_cap(self):
        r = self.run_sb('cmd', '/c', 'cmd /c cmd /c cmd /c echo deep', procs=2)
        self.assertNotIn('deep', r.output)

    def test_timeout_kills_the_tree(self):
        (self.work / 'outer.cmd').write_text('@call inner.cmd\r\n')
        (self.work / 'inner.cmd').write_text('@echo started\r\n:loop\r\n@goto loop\r\n')
        r = self.run_sb('cmd', '/c', 'outer.cmd', timeout_s=3)
        self.assertTrue(r.timed_out, r.output)
        self.assertEqual(r.code, 124)
        self.assertLess(r.seconds, 20)
        self.assertIn('started', r.output)

    def test_children_do_not_outlive_the_step(self):
        (self.work / 'spawn.cmd').write_text('@start "" /b cmd /c "ping -n 40 -w 1000 127.0.0.2 >nul"\r\n@echo spawned\r\n')
        r = self.run_sb('cmd', '/c', 'spawn.cmd', timeout_s=30)
        self.assertIn('spawned', r.output)
        self.assertGreaterEqual(r.processes, 2)
        self.assertLess(r.seconds, 20, 'the parent must not wait for the background child')
        ps = subprocess.run(['powershell', '-NoProfile', '-Command',
                             "@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'PING.EXE' -and $_.CommandLine -like '*127.0.0.2*' }).Count"],
                            capture_output=True, text=True)
        self.assertEqual(ps.stdout.strip(), '0', 'background child survived the step')

    def test_volume_root_is_list_only(self):
        self.run_sb('cmd', '/c', 'echo x> C:\\jarvis-evil.txt')
        self.assertFalse(Path('C:/jarvis-evil.txt').exists())
        r = self.run_sb('cmd', '/c', f'type "{Path.home() / ".gitconfig"}"')
        self.assertNotEqual(r.code, 0)

    def test_java_build_inside(self):
        src = self.work / 'src'
        src.mkdir()
        (src / 'Hallo.java').write_text('public class Hallo { public static void main(String[] a) { System.out.println("hallo-aus-sandbox"); } }')
        r = self.run_sb('javac', '-d', 'classes', 'src/Hallo.java')
        self.assertEqual(r.code, 0, r.output)
        r = self.run_sb('jar', 'cf', 'hallo.jar', '-C', 'classes', '.')
        self.assertEqual(r.code, 0, r.output)
        r = self.run_sb('java', '-cp', 'hallo.jar', 'Hallo')
        self.assertEqual(r.code, 0, r.output)
        self.assertIn('hallo-aus-sandbox', r.output)
        self.assertGreater(r.peak_mem_mb, 1)


@unittest.skipUnless(WIN, 'Windows only')
class Worker(unittest.TestCase):
    """java.build as the PC worker runs it (jarvis.py), always inside the sandbox."""
    @classmethod
    def setUpClass(cls):
        import jarvis
        cls.j = jarvis

    def setUp(self):
        self.work = w.new_workdir('wtest')
        self.addCleanup(w.cleanup, self.work)

    def test_selftest_reports_tested(self):
        self.assertEqual(self.j.pc_probe()['java.build']['status'], 'tested')

    def test_plain_java_build(self):
        (self.work / 'src').mkdir()
        (self.work / 'src' / 'A.java').write_text('public class A { public static void main(String[] a) {} }')
        ok, detail = self.j.java_build(self.work, {})
        self.assertTrue(ok, detail)
        self.assertIn('Netz aus', detail)
        self.assertTrue((self.work / 'build' / 'libs' / 'work.jar').is_file())

    def test_gradle_build_offline(self):
        if not list(self.j.GRADLE_HOME.glob('wrapper/dists/gradle-*-bin/*/gradle-*/bin/gradle.bat')):
            self.skipTest('kein Gradle im JARVIS-Gradle-Home (pc-gradle-seed)')
        (self.work / 'settings.gradle').write_text("rootProject.name = 'mini'\n")
        (self.work / 'build.gradle').write_text("plugins { id 'java' }\n")
        (self.work / 'src/main/java/demo').mkdir(parents=True)
        (self.work / 'src/main/java/demo/H.java').write_text('package demo; public class H {}')
        ok, detail = self.j.java_build(self.work, {})
        self.assertTrue(ok, detail)
        self.assertTrue((self.work / 'build' / 'libs' / 'mini.jar').is_file())

    def test_gradle_cannot_download_without_network_permission(self):
        if not list(self.j.GRADLE_HOME.glob('wrapper/dists/gradle-*-bin/*/gradle-*/bin/gradle.bat')):
            self.skipTest('kein Gradle im JARVIS-Gradle-Home')
        (self.work / 'settings.gradle').write_text("rootProject.name = 'dl'\n")
        (self.work / 'build.gradle').write_text("plugins { id 'java' }\nrepositories { mavenCentral() }\n"
                                                "dependencies { implementation 'org.jetbrains:annotations:1.0.0-jarvis-does-not-exist' }\n")
        (self.work / 'src/main/java/demo').mkdir(parents=True)
        (self.work / 'src/main/java/demo/H.java').write_text('package demo; public class H {}')
        ok, detail = self.j.java_build(self.work, {})
        self.assertFalse(ok)
        self.assertIn('offline', detail.lower())

    def test_junctions_are_never_collected(self):
        d = Path(tempfile.mkdtemp(prefix='jarvis-canary-'))
        self.addCleanup(shutil.rmtree, d, True)
        (d / 'secret.txt').write_text('CANARY')
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(self.work / 'leak'), str(d)], capture_output=True, check=True)
        self.addCleanup(lambda: os.path.isdir(self.work / 'leak') and os.rmdir(self.work / 'leak'))
        (self.work / 'ok.txt').write_text('x')
        names = {p.name for p in self.j.safe_files(self.work)}
        self.assertIn('ok.txt', names)
        self.assertNotIn('secret.txt', names)


if __name__ == '__main__':
    unittest.main()
