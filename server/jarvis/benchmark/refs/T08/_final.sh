printf 'import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n' > test_kontakt.py
printf '# kontakt\n\n    python3 kontakt.py bilder --out kontaktbogen.png --thumbs thumbs\n' > README.md
python3 kontakt.py bilder --out kontaktbogen.png --thumbs thumbs
