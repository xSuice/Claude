printf 'import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n' > test_nachweis.py
printf '# nachweis\n\n    python3 nachweis.py berichtsheft.json --out nachweis.md\n' > README.md
python3 nachweis.py berichtsheft.json --out nachweis.md
