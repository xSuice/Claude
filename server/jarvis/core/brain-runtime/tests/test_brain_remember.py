"""PRIO2 N4: „Merk dir …“ / „Was weißt du über mich?“ / „Vergiss …“ über das bestehende Brain (bestätigte Fakten mit Herkunft)."""
import json, os, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from brain_core import Brain  # noqa: E402


class RememberTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.b = Brain(self.dir / 'brain.db', 'andrew', {'jarvis'})

    def test_remember_stores_confirmed_preference_with_provenance(self):
        r = self.b.remember('jarvis', 'Ich bevorzuge Java 21 für Minecraft-Plugins', 'portal:andrew')
        self.assertEqual(r['status'], 'confirmed')
        rows = self.b.list_confirmed('jarvis')['items']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['content'], 'Ich bevorzuge Java 21 für Minecraft-Plugins')
        self.assertEqual(rows[0]['kind'], 'preference')
        self.assertIn('portal:andrew', rows[0]['source'])
        self.assertIn('Owner bestätigt', rows[0]['source'])
        # wiederfindbar über die bestehende Suche
        self.assertEqual(self.b.recall('jarvis', 'Java Minecraft Plugins')['items'][0]['id'], r['id'])

    def test_secrets_are_refused_and_nothing_stored(self):
        for t in ('Mein API Key ist sk-ant-A1b2C3d4E5f6G7h8I9j0K', 'passwort: Hunter2Secure99x'):
            with self.assertRaises(ValueError):
                self.b.remember('jarvis', t, 'portal:andrew')
        with sqlite3.connect(self.dir / 'brain.db') as c:
            self.assertEqual(c.execute('select count(*) from memory').fetchone()[0], 0)

    def test_length_and_project_limits(self):
        for t in ('', 'ab', 'x' * 501):
            with self.assertRaises(ValueError):
                self.b.remember('jarvis', t, 'portal:andrew')
        with self.assertRaises(Exception):
            self.b.remember('fremdes-projekt', 'Ich mag Tee', 'portal:andrew')

    def test_list_only_own_confirmed_newest_first_and_forget(self):
        a = self.b.remember('jarvis', 'Ich trinke morgens Tee', 'portal:andrew')
        b = self.b.remember('jarvis', 'Mein Server heißt ma-server', 'portal:andrew')
        self.b.propose('jarvis', 'Hypothese', 'nur vorgeschlagen', 'claude job x', 'hypothesis')   # unbestätigt: nie gelistet
        other = Brain(self.dir / 'brain.db', 'philipp', {'jarvis'})
        other.remember('jarvis', 'Fremde Vorliebe 123', 'portal:philipp')
        ids = [x['id'] for x in self.b.list_confirmed('jarvis')['items']]
        self.assertEqual(ids, [b['id'], a['id']] if ids[0] == b['id'] else ids)   # neueste zuerst (gleiche Sekunde: stabil)
        self.assertEqual(set(ids), {a['id'], b['id']})
        self.b.retract(a['id'])
        self.assertEqual([x['id'] for x in self.b.list_confirmed('jarvis')['items']], [b['id']])

    def test_list_limit_bounds(self):
        for i in range(25):
            self.b.remember('jarvis', 'Fakt Nummer %d ist wahr' % i, 'portal:andrew')
        self.assertEqual(len(self.b.list_confirmed('jarvis', limit=50)['items']), 20)
        self.assertEqual(len(self.b.list_confirmed('jarvis', limit=3)['items']), 3)


if __name__ == '__main__':
    unittest.main()
