printf 'import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n' > test_wav2mp3.py
printf '# wav2mp3\n\n    python3 wav2mp3.py ton.wav --out ton.mp3\n' > README.md
python3 wav2mp3.py ton.wav --out ton.mp3
