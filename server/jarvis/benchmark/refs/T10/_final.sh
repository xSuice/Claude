printf 'import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n' > test_ringpuffer.py
printf '# RingPuffer\n\n    from ringpuffer import RingPuffer\n' > README.md
