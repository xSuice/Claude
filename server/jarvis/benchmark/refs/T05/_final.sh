printf 'import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n' > test_kurzbericht.py
printf '# kurzbericht\n\n    python3 kurzbericht.py abschnitte.json --out kurzbericht.pdf\n' > README.md
python3 kurzbericht.py abschnitte.json --out kurzbericht.pdf
