"""Kurze Schlüsselwörter nur am Wortanfang (Live-Befund 28.10.2026: Markdown -> critical)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from task_classifier import TaskClassifier  # noqa: E402


class Boundaries(unittest.TestCase):
    def test_markdown_is_not_an_outage(self):
        self.assertEqual(TaskClassifier().classify("Schreibe eine Markdown-Datei mit drei Sätzen")["complexity"], "routine")

    def test_real_critical_words_still_match(self):
        c = TaskClassifier()
        self.assertEqual(c.classify("Server down seit heute")["complexity"], "critical")
        self.assertEqual(c.classify("Downtime im Portal")["complexity"], "critical")
        self.assertEqual(c.classify("P1 Incident")["complexity"], "critical")
        self.assertEqual(c.classify("Systemabsturz nach Update")["complexity"], "critical")   # lange Wörter weiter als Teilwort


if __name__ == "__main__":
    unittest.main()
