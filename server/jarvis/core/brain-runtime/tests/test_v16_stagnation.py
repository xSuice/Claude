"""Anti-Stagnation: derselbe Fehler (normalisierte Signatur) führt nicht zu einer weiteren gleichen Wiederholung."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v16_fakes import FakeClaude, WC_PLAN, make_app, run_until, tmpdir, wc_steps  # noqa: E402

import sandbox  # noqa: E402
from taskengine import Engine  # noqa: E402

LINUX = sys.platform == 'linux' and sandbox.available()


class Signature(unittest.TestCase):
    def test_same_error_with_other_numbers_and_paths_has_same_signature(self):
        a = Engine.failure_signature('s2', 'FAIL test_x (line 12) in /tmp/w1/a.py after 120 ms')
        b = Engine.failure_signature('s2', 'FAIL test_x (line 13) in /tmp/w9/a.py after 98 ms')
        self.assertEqual(a, b)
        self.assertNotEqual(a, Engine.failure_signature('s2', 'ImportError: no module named foo'))
        self.assertNotEqual(a, Engine.failure_signature('s3', 'FAIL test_x (line 12) in /tmp/w1/a.py after 120 ms'))


@unittest.skipUnless(LINUX, 'needs Linux with a sandbox backend')
class InEngine(unittest.TestCase):
    def test_identical_failure_stops_early(self):
        steps = wc_steps()
        steps['Code und Tests schreiben'] = lambda cwd, prompt, n: (_ for _ in ()).throw(RuntimeError('x')) if False else None
        fake = FakeClaude(WC_PLAN, {k: (lambda cwd, prompt, n: None) for k in steps})   # schreibt nie die erwarteten Dateien
        eng = make_app(tmpdir(self), fake, job_defaults={'step_attempts': 5})
        j = eng.submit('Wortzähler mit Tests')
        st = run_until(eng, job=j['job_id'])
        kinds = [e['kind'] for e in eng.events(j['job_id'])]
        self.assertIn('stagnation', kinds)
        worker_calls = [c for c in fake.calls if not c['planning']]
        self.assertEqual(len(worker_calls), 2)        # 1. Versuch, 1 Wiederholung mit Rückmeldung, dann Stopp statt 5 Versuche
        self.assertIn(st['state'], ('failed', 'partial'))


if __name__ == '__main__':
    unittest.main()
