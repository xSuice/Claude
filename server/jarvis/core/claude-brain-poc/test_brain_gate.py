import unittest
from brain_gate import make_pack


class BrainGateTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            {"title": "Server-Port", "content": "Der Testserver ist derzeit unter Port 3000 erreichbar.", "source": "status/api", "version": "2026-10-14", "status": "confirmed", "project": "ma-home", "visibility": "shared"},
            {"title": "Alter Server-Port", "content": "Der Testserver ist derzeit unter Port 8080 erreichbar.", "source": "old-plan", "version": "1", "status": "confirmed", "retracted": True, "project": "ma-home", "visibility": "shared"},
            {"title": "Privat", "content": "Persönlicher Schlüssel server 9999", "source": "personal", "version": "1", "status": "confirmed", "project": "ma-home", "visibility": "private", "owner": "person-b"},
            {"title": "Fremdprojekt", "content": "Server 1234", "source": "other", "version": "1", "status": "confirmed", "project": "other-project", "visibility": "shared"},
        ]

    def test_retrieval_excludes_retracted_and_other_user(self):
        result = make_pack({"query": "Server Port", "candidates": self.records}, "person-a", "ma-home", 3000)
        text = str(result["items"])
        self.assertIn("3000", text)
        self.assertNotIn("8080", text)
        self.assertNotIn("9999", text)
        self.assertNotIn("1234", text)

    def test_no_evidence(self):
        result = make_pack({"query": "Filmabend", "candidates": self.records}, "person-a", "ma-home", 3000)
        self.assertEqual(result["items"], [])
        self.assertIsNotNone(result["warning"])

    def test_budget_no_partial_evidence(self):
        long_item = dict(self.records[0], content="Server " + ("sehr langer Inhalt " * 30))
        result = make_pack({"query": "Server", "candidates": [long_item]}, "person-a", "ma-home", 150)
        self.assertEqual(result["items"], [])

    def test_duplicate_content(self):
        records = [self.records[0], dict(self.records[0])]
        result = make_pack({"query": "Server", "candidates": records}, "person-a", "ma-home", 3000)
        self.assertEqual(len(result["items"]), 1)

    def test_unknown_status_is_not_confirmed(self):
        rec = dict(self.records[0], status="hypothesis")
        result = make_pack({"query": "Server", "candidates": [rec]}, "person-a", "ma-home", 3000)
        self.assertEqual(result["items"], [])


if __name__ == "__main__":
    unittest.main()
