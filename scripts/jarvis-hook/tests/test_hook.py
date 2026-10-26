import json, os, socket, subprocess, sys, tempfile, threading, unittest
HOOK = os.path.join(os.path.dirname(__file__), "..", "jarvis-submit-hook.py")


class Fake:
    def __init__(self, path, antwort):
        self.n, self.reqs = 0, []
        self.srv = socket.socket(socket.AF_UNIX); self.srv.bind(path); self.srv.listen(5)
        self.antwort = antwort
        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self):
        while True:
            try:
                c, _ = self.srv.accept()
            except OSError:
                return
            d = b""
            while not d.endswith(b"\n"):
                d += c.recv(65536)
            self.n += 1; self.reqs.append(json.loads(d))
            c.sendall(json.dumps(self.antwort).encode() + b"\n"); c.close()


def run(prompt, sock, env_extra=None, sid="s1"):
    env = dict(os.environ, JARVIS_BRIDGE_SOCK=sock, HOME=tempfile.mkdtemp()); env.pop("JARVIS_WORKER", None)
    env.update(env_extra or {})
    r = subprocess.run([sys.executable, "-I", HOOK], input=json.dumps({"prompt": prompt, "session_id": sid}), capture_output=True, text=True, env=env)
    return r.returncode, r.stdout


class T(unittest.TestCase):
    def setUp(self):
        self.sock = os.path.join(tempfile.mkdtemp(), "b.sock")
        self.f = Fake(self.sock, {"ok": True, "data": {"job_id": "j-test-1"}})

    def test_trigger_submits_once_with_stable_client_id(self):
        c, o = run("jarvis: schreibe slug.py", self.sock); self.assertEqual(c, 0); self.assertIn("j-test-1", o)
        run("jarvis: schreibe slug.py", self.sock)
        self.assertEqual(self.f.n, 2)
        self.assertEqual(self.f.reqs[0]["client_id"], self.f.reqs[1]["client_id"])
        self.assertEqual(self.f.reqs[0]["request"], "schreibe slug.py")

    def test_normal_chat_untouched(self):
        c, o = run("wie spät ist es", self.sock); self.assertEqual((c, o, self.f.n), (0, "", 0))

    def test_worker_never_forwards(self):
        c, o = run("jarvis: x", self.sock, {"JARVIS_WORKER": "1"}); self.assertEqual((o, self.f.n), ("", 0))

    def test_trigger_in_middle_ignored(self):
        run("bitte jarvis: mach was", self.sock); self.assertEqual(self.f.n, 0)

    def test_direkt_bypass(self):
        run("direkt: jarvis: reparatur", self.sock); self.assertEqual(self.f.n, 0)

    def test_bridge_down_fail_open_unknown(self):
        c, o = run("jarvis: x", "/nonexistent/sock"); self.assertEqual(c, 0); self.assertIn("UNBEKANNT", o)

    def test_rejected(self):
        self.f.antwort = {"ok": False, "error": "plan_block"}
        c, o = run("jarvis: x", self.sock); self.assertIn("NICHT angenommen", o)


unittest.main()
