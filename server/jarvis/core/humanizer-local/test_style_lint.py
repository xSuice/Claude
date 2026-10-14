import unittest
from style_lint import lint


class StyleLintTests(unittest.TestCase):
    def test_german_phrase(self):
        found = lint('Es ist wichtig zu beachten, dass dies ein Test ist.')
        self.assertEqual(found[0]['kind'], 'phrase')

    def test_english_phrase(self):
        found = lint('It is important to note that the data is incomplete.')
        self.assertEqual(len(found), 1)

    def test_fenced_code_ignored(self):
        found = lint('```python\nprint("In conclusion, good")\n```')
        self.assertEqual(found, [])

    def test_frontmatter_ignored(self):
        found = lint('---\ntitle: In conclusion\n---\nNormaler Text.')
        self.assertEqual(found, [])

    def test_indented_code_ignored(self):
        self.assertEqual(lint('    In conclusion, test code line'), [])

    def test_prose_without_flags(self):
        self.assertEqual(lint('Heute habe ich den Fehler im Login gefunden und behoben.'), [])


if __name__ == '__main__':
    unittest.main()
