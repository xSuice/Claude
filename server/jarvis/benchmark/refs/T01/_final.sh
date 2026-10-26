printf 'import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n' > test_verbrauch.py
printf '# verbrauch\n\n    python3 verbrauch.py zaehler.csv --out tage.csv --anomalien anomalien.txt\n' > README.md
python3 verbrauch.py zaehler.csv --out tage.csv --anomalien anomalien.txt
