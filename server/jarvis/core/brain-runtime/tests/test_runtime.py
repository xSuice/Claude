import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "brain-runtime"))
from gateway import KnowledgeGateway
from mcp_server import Server
from evaluate import evaluate

DATA = ROOT / "brain-runtime" / "fixtures" / "knowledge.jsonl"


class ReadOnlyBrainTests(unittest.TestCase):
    def setUp(self):
        self.store = KnowledgeGateway(DATA, "person-a", {"ma-home"})

    def test_authorized_and_retracted(self):
        r = self.store.search("Testserver Port aktiv", "ma-home")
        self.assertEqual([x["id"] for x in r["items"]], ["port-live"])

    def test_private_isolation(self):
        self.assertNotIn("private-b", [x["id"] for x in self.store.search("rotgrüne", "ma-home")["items"]])
        self.assertEqual([x["id"] for x in self.store.search("blauviolette", "ma-home")["items"]], ["private-a"])

    def test_shared_must_grant_receiver(self):
        g = KnowledgeGateway(DATA, "person-c", {"ma-home"})
        self.assertEqual(g.search("Testserver Port", "ma-home")["items"], [])

    def test_weak_partial_match_not_returned(self):
        self.assertEqual(self.store.search("Privat B rotgrüne", "ma-home")["items"], [])

    def test_no_user_project_override(self):
        with self.assertRaises(PermissionError):
            self.store.search("Aragorn", "novel")
        self.assertFalse(self.store.search("Aragorn", "ma-home")["items"])

    def test_retraction_read_on_next_request(self):
        with tempfile.TemporaryDirectory() as d:
            dst = Path(d)/"data.jsonl"
            dst.write_text(DATA.read_text(encoding="utf-8"), encoding="utf-8")
            gate = KnowledgeGateway(dst, "person-a", {"ma-home"})
            self.assertTrue(gate.search("blauviolette", "ma-home")["items"])
            items = [json.loads(x) for x in dst.read_text(encoding="utf-8").splitlines()]
            for x in items:
                if x["id"] == "private-a":
                    x["retracted"] = True
            dst.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in items)+"\n", encoding="utf-8")
            self.assertFalse(gate.search("blauviolette", "ma-home")["items"])

    def test_budget(self):
        r = self.store.search("Testserver Port aktiv", "ma-home", max_chars=200)
        self.assertLessEqual(sum(len(json.dumps(item, ensure_ascii=False)) for item in r["items"]), 200)
        self.assertTrue(r["items"])

    def test_eval_fixture(self):
        cases = json.loads((ROOT/"brain-runtime"/"evals"/"cases.json").read_text(encoding="utf-8"))
        result = evaluate(self.store, cases)
        self.assertEqual(result["passed"], result["total"])

    def test_mcp_dispatch(self):
        server = Server({"identity":"person-a","allowed_projects":["ma-home"],"source":str(DATA),"research_tools":True})
        init = server.dispatch({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}})
        self.assertEqual(init["result"]["serverInfo"]["name"], "claude-local-brain")
        tools = server.dispatch({"jsonrpc":"2.0","id":2,"method":"tools/list"})
        self.assertEqual(len(tools["result"]["tools"]), 3)
        data = server.dispatch({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"brain_lookup","arguments":{"query":"Port aktiv","project":"ma-home"}}})
        self.assertIn("port-live", data["result"]["content"][0]["text"])
        self.assertIsNone(server.dispatch({"jsonrpc":"2.0","method":"notifications/initialized"}))

    def test_mcp_lab_real_edges(self):
        server = Server({"identity":"person-a","allowed_projects":["ma-home"],"source":str(DATA),"research_tools":True})
        result = server.call("brain_openworm_probe", {"neuron":"I1L", "steps":2})
        self.assertFalse(result.get("isError", False), result)
        self.assertIn("I1L", result["content"][0]["text"])

    def test_mcp_stdio_subprocess(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d)/"brain.json"
            cfg.write_text(json.dumps({"identity":"person-a","allowed_projects":["ma-home"],"source":str(DATA),"research_tools":False}))
            payload = '\n'.join(json.dumps(x) for x in [
                {"jsonrpc":"2.0","id":1,"method":"initialize","params":{}},
                {"jsonrpc":"2.0","method":"notifications/initialized"},
                {"jsonrpc":"2.0","id":2,"method":"tools/list"},
                {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"brain_lookup","arguments":{"query":"Port aktiv","project":"ma-home"}}},
            ]) + '\n'
            proc = subprocess.run([sys.executable, str(ROOT/"brain-runtime"/"mcp_server.py"), "--config", str(cfg)],
                                  input=payload, capture_output=True, text=True, timeout=10)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            responses = [json.loads(x) for x in proc.stdout.splitlines()]
            self.assertEqual([x["id"] for x in responses], [1,2,3])
            self.assertIn("port-live", responses[-1]["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
