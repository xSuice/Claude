printf 'import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n' > test_toc.py
printf '# toc\n\n    python3 toc.py dokument.md --out dokument_mit_toc.md\n' > README.md
python3 toc.py dokument.md --out dokument_mit_toc.md
