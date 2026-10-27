import unittest
from router_core import choose, suggest_access

class AckRouting(unittest.TestCase):
    def test_exact_ack_uses_small_model(self):
        self.assertEqual(choose('Antworte nur mit OK', mode='lesen')[0], 'haiku')

    def test_ack_does_not_downgrade_images(self):
        self.assertNotEqual(choose('Antworte nur mit OK', mode='lesen', has_images=True)[0], 'haiku')

    def test_ack_does_not_override_manual(self):
        self.assertEqual(choose('Antworte nur mit OK', manual='opus')[0], 'opus')

    def test_extra_instructions_do_not_match_ack(self):
        for text in ['Antworte nur mit OK und implementiere ein Skript',
                     'Antworte nur mit OK nachdem du eine Sicherheitsarchitektur entworfen hast',
                     'Antworte nur mit OK und lösche die Datei',
                     'AI-Council: Antworte nur mit OK']:
            with self.subTest(text=text):
                self.assertNotEqual(choose(text)[0], 'haiku')

    def test_ack_does_not_grant_access(self):
        self.assertEqual(suggest_access('Antworte nur mit OK'), ('lesen','notizen',False))

if __name__=='__main__': unittest.main()
