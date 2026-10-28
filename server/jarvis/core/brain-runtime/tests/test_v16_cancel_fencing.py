"""Abbruch-Fencing (Live-Befund 28.10.2026, Job j20261028-aaf5f2): ein Abbruch waehrend einer laufenden Planung, eines
Schritts oder einer Council-Rolle darf vom spaeten Ergebnis nicht ueberschrieben werden. Linux (sandbox) only."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v16_fakes import FakeClaude, WC_PLAN, make_app, run_until, tmpdir, wc_steps  # noqa: E402

import sandbox  # noqa: E402

LINUX = sys.platform == 'linux' and sandbox.available()


@unittest.skipUnless(LINUX, 'needs Linux with a sandbox backend')
class CancelFencing(unittest.TestCase):
    def test_cancel_during_planning_is_not_overwritten(self):
        box = {}

        def plan(prompt):
            box['eng'].cancel(box['job'])        # Philipp bricht ab, während der Planer noch arbeitet
            return WC_PLAN
        fake = FakeClaude(plan, wc_steps())
        eng = make_app(tmpdir(self), fake)
        j = eng.submit('Wortzähler mit Tests')
        box.update(eng=eng, job=j['job_id'])
        eng.tick(max_seconds=0)
        st = eng.status(j['job_id'])
        self.assertEqual(st['state'], 'cancelled')
        self.assertEqual(st['steps'], [])                       # kein Plan der abgebrochenen Planung gespeichert
        self.assertNotIn('planned', [e['kind'] for e in eng.events(j['job_id'])])
        run_until(eng, job=j['job_id'], rounds=3)
        self.assertEqual(eng.status(j['job_id'])['state'], 'cancelled')
        self.assertEqual(fake.planning_calls, 1)

    def test_cancel_during_step_discards_result(self):
        box = {}
        steps = wc_steps()
        orig = steps['Code und Tests schreiben']

        def code(cwd, prompt, n):
            out = orig(cwd, prompt, n)
            box['eng'].cancel(box['job'])
            return out
        steps['Code und Tests schreiben'] = code
        eng = make_app(tmpdir(self), FakeClaude(WC_PLAN, steps))
        j = eng.submit('Wortzähler mit Tests')
        box.update(eng=eng, job=j['job_id'])
        st = run_until(eng, job=j['job_id'])
        self.assertEqual(st['state'], 'cancelled')
        self.assertNotIn('step_done', [e['kind'] for e in eng.events(j['job_id'])])

    def test_cancel_during_council_stops_round(self):
        box = {}

        def opinion(prompt):
            box['eng'].cancel(box['job'])
            return {'recommendation': 'x', 'constraints': [], 'risks': [], 'objections': [], 'block': False, 'confidence': 0.5}
        fake = FakeClaude(WC_PLAN, wc_steps(), council=opinion)
        eng = make_app(tmpdir(self), fake, cfg_extra={'council': {'enabled': True, 'max_roles': 3}})
        j = eng.submit('Wortzähler bauen und danach mit sudo systemctl restart nginx neu starten')
        box.update(eng=eng, job=j['job_id'])
        run_until(eng, job=j['job_id'])
        self.assertEqual(eng.status(j['job_id'])['state'], 'cancelled')
        self.assertEqual(len(fake.council_calls), 1)            # keine weiteren Rollen nach dem Abbruch
        self.assertEqual(fake.planning_calls, 0)


if __name__ == '__main__':
    unittest.main()
