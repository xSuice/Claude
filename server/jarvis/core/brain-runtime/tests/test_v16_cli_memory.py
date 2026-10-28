"""PRIO2 N4 auf CLI-Ebene (echte Prozessaufrufe wie die Brücke): remember / memories / forget memory."""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_v16_cli import Cli, LINUX  # noqa: E402


@unittest.skipUnless(LINUX, 'needs Linux with a sandbox backend')
class CliMemory(Cli):
    def test_full_cycle(self):   # geerbter Volltest hier nicht doppelt ausführen
        pass

    def test_remember_list_forget(self):
        code, r = self.run_cli('remember', '--text', 'Ich bevorzuge Java 21 für Plugins', '--by', 'portal:andrew')
        self.assertEqual(code, 0, r)
        self.assertEqual(r['status'], 'confirmed')
        code, m = self.run_cli('memories')
        self.assertEqual(code, 0, m)
        self.assertEqual([x['content'] for x in m['items']], ['Ich bevorzuge Java 21 für Plugins'])
        self.assertNotIn('owner', m['items'][0])
        code, f = self.run_cli('forget', 'memory', r['id'])
        self.assertEqual((code, f['status']), (0, 'retracted'))
        self.assertEqual(self.run_cli('memories')[1]['items'], [])

    def test_secret_refused_with_clean_error(self):
        code, r = self.run_cli('remember', '--text', 'Mein Token ist ghp_' + 'a' * 10 + 'B1' * 8, '--by', 'portal:andrew')
        self.assertNotEqual(code, 0)
        self.assertIn('Zugangsdatum', r.get('error', ''))
        self.assertNotIn('ghp_', json.dumps(r))                 # Wert wird nicht zurückgespiegelt
        self.assertEqual(self.run_cli('memories')[1]['items'], [])


if __name__ == '__main__':
    unittest.main()
