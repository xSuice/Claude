"""Living HQ: Figuren nur aus echten Engine-Ereignissen (AgentEvents), kein Phantom-Arbeiten nach Abschluss/Abbruch."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v16_fakes import FakeClaude, WC_PLAN, make_app, run_until, tmpdir, wc_steps  # noqa: E402

import sandbox  # noqa: E402

LINUX = sys.platform == 'linux' and sandbox.available()


@unittest.skipUnless(LINUX, 'needs Linux with a sandbox backend')
class Activity(unittest.TestCase):
    def test_events_are_normalized_to_agents(self):
        fake = FakeClaude(WC_PLAN, wc_steps())
        eng = make_app(tmpdir(self), fake, cfg_extra={'council': {'enabled': True, 'max_roles': 2}})
        j = eng.submit('Wortzähler bauen und danach mit sudo systemctl restart nginx neu starten')
        run_until(eng, job=j['job_id'])
        act = eng.agent_activity()
        agents = {e['agent'] for e in act['events']}
        self.assertIn('jarvis-security', agents)            # Council-Rolle -> Fachprofil
        self.assertIn('jarvis-planner', agents)
        self.assertTrue(all(e['agent'].startswith('jarvis-') for e in act['events']))
        self.assertEqual(act['agents'], {})                 # nichts läuft gerade: keine arbeitende Figur
        later = eng.agent_activity(since_id=act['last_id'])
        self.assertEqual(later['events'], [])

    def test_open_call_shows_busy_until_job_is_final(self):
        fake = FakeClaude(WC_PLAN, wc_steps())
        eng = make_app(tmpdir(self), fake)
        j = eng.submit('Wortzähler mit Tests')
        eng.event(j['job_id'], 'claude', 'Schritt s9: Claude sonnet gestartet')
        self.assertEqual(eng.agent_activity()['agents']['jarvis-core']['job'], j['job_id'])
        eng.cancel(j['job_id'])
        self.assertEqual(eng.agent_activity()['agents'], {})


if __name__ == '__main__':
    unittest.main()
