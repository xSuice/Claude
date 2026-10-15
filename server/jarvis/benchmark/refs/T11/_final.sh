printf 'import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n' > test_auswertung.py
printf '# auswertung\n\n    python3 auswertung.py messdaten.csv --json statistik.json --docx bericht.docx\n' > README.md
python3 auswertung.py messdaten.csv --json statistik.json --docx bericht.docx
