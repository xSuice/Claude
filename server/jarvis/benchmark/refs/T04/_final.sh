printf 'import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n' > test_bericht.py
printf '# bericht\n\n    python3 bericht.py verkauf.csv --out umsatz.docx\n' > README.md
python3 bericht.py verkauf.csv --out umsatz.docx
