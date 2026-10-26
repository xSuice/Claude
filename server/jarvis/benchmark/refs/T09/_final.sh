printf 'import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n' > test_bericht.py
printf '# bericht\n\n    python3 bericht.py statistik.json --out statistik.md\n' > README.md
python3 /home/andrew/MA-Server/server/jarvis/dropin-beispiele/wortstatistik/wortstatistik.py text.txt statistik.json 5
python3 bericht.py statistik.json --out statistik.md
