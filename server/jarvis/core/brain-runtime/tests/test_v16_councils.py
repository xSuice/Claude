"""Fach-Councils: nur bei komplexen/riskanten Auftraegen, werkzeuglos (beratend), Decision Artifact je Revision,
Randbedingungen fliessen in die Planung, Block-Votum erzwingt Plan-Freigabe, Unterbrechung ohne Doppelbefragung, messbar."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v16_fakes import FakeClaude, WC_PLAN, make_app, run_until, tmpdir, wc_steps  # noqa: E402

import council  # noqa: E402
import sandbox  # noqa: E402

LINUX = sys.platform == 'linux' and sandbox.available()
ON = {'council': {'enabled': True, 'max_roles': 3}}
RISKY = 'Wortzähler mit Tests bauen und danach mit sudo systemctl restart nginx den Dienst neu starten'


class Selection(unittest.TestCase):
    def test_simple_request_needs_no_council(self):
        self.assertIsNone(council.select('Wortzähler mit Tests', {'effects': [], 'risk': 'read'})[0])

    def test_privileged_forces_security(self):
        self.assertEqual(council.select(RISKY, {'effects': ['privileged'], 'risk': 'privileged'})[0], 'SECURITY')

    def test_explicit_and_topic(self):
        self.assertEqual(council.select('bitte im council beraten: Python-Skript und API-Test', {'effects': []})[0], 'DEV')
        self.assertEqual(council.select('x', {'effects': [], 'council': 'CREATIVE'})[0], 'CREATIVE')
        self.assertIsNone(council.select('x' * 700, {'effects': [], 'council': 'off'})[0])

    def test_eight_councils_max_five_roles_bound_to_profiles(self):
        self.assertEqual(set(council.COUNCILS), {'DEV', 'CLOUD', 'AI', 'SECURITY', 'OPERATIONS', 'STRATEGY', 'DATA', 'CREATIVE'})
        for c in council.COUNCILS.values():
            self.assertLessEqual(len(c['roles']), 5)
            self.assertTrue(all(p.startswith('jarvis-') for _, p, _ in c['roles']))

    def test_unreadable_opinion_becomes_dissent(self):
        o = council.parse_opinion('kein json')
        self.assertFalse(o['valid'])
        a = council.merge('DEV', 'x', {'Architekt': o}, 'j1', 1)
        self.assertEqual(a['dissent'], ['Architekt: Antwort nicht auswertbar'])
        self.assertTrue(a['approved_for_execution'])


@unittest.skipUnless(LINUX, 'needs Linux with a sandbox backend')
class InEngine(unittest.TestCase):
    def test_simple_job_skips_council(self):
        fake = FakeClaude(WC_PLAN, wc_steps())
        eng = make_app(tmpdir(self), fake, cfg_extra=ON)
        j = eng.submit('Wortzähler mit Tests')
        st = run_until(eng, job=j['job_id'])
        self.assertEqual(st['state'], 'done', st['summary'])
        self.assertEqual(fake.council_calls, [])
        self.assertIn('council_skip', [e['kind'] for e in eng.events(j['job_id'])])
        self.assertEqual(eng.council_metrics()['skipped_simple'], 1)

    def test_risky_job_gets_tool_less_security_council_and_planner_constraints(self):
        fake = FakeClaude(WC_PLAN, wc_steps(), council=lambda p: {'recommendation': 'vorher Backup', 'constraints': ['Vorher Konfiguration sichern'],
                                                                    'risks': ['Dienst fällt aus'], 'objections': ['Neustart nachts'],
                                                                    'block': False, 'confidence': 0.9})
        eng = make_app(tmpdir(self), fake, cfg_extra=ON)
        j = eng.submit(RISKY)
        st = run_until(eng, job=j['job_id'])
        self.assertEqual(st['state'], 'waiting_approval')            # privileged needs plan approval anyway
        self.assertEqual(len(fake.council_calls), 3)
        self.assertTrue(all(c['tools'] == '' for c in fake.calls if c['council']))   # technisch nur beratend
        plan_prompt = next(c['prompt'] for c in fake.calls if c['planning'])
        self.assertIn('COUNCIL-BESCHLUSS (SECURITY', plan_prompt)
        self.assertIn('Vorher Konfiguration sichern', plan_prompt)
        a = st['council']
        self.assertEqual((a['council'], a['revision'], len(a['roles']), a['advisory_only']), ('SECURITY', 1, 3, True))
        self.assertEqual(len(a['dissent']), 3)
        self.assertEqual(a['constraints'], ['Vorher Konfiguration sichern'])   # dedupliziert
        m = eng.council_metrics()['councils']['SECURITY']
        self.assertEqual((m['rounds'], m['done'], m['calls']), (1, 1, 3))
        self.assertGreater(m['tokens'], 0)
        self.assertEqual(m['avg_confidence'], 0.9)

    def test_block_vote_forces_plan_approval_on_otherwise_unapproved_job(self):
        fake = FakeClaude(WC_PLAN, wc_steps(), council=lambda p: {'recommendation': 'nein', 'constraints': [], 'risks': [],
                                                                    'objections': ['personenbezogene Daten'], 'block': 'COUNCIL-ROLLE: Identität' in p,
                                                                    'confidence': 0.7})
        eng = make_app(tmpdir(self), fake, cfg_extra=ON)
        j = eng.submit('Bitte im Council beraten: Wortzähler mit Tests', options={'council': 'SECURITY'})
        st = run_until(eng, job=j['job_id'])
        self.assertEqual(st['state'], 'waiting_approval')
        self.assertEqual(st['council']['blocked_by'], ['Identität/Geheimnisse'])
        self.assertFalse(st['council']['approved_for_execution'])

    def test_deferred_council_resumes_without_re_asking_roles(self):
        fake = FakeClaude(WC_PLAN, wc_steps())
        block = {'on': True}

        def probe():   # nach der ersten Rollenbefragung ist das Plan-Kontingent voll (zurückstellen statt verbrauchen)
            return {'ok': True, 'five': {'p': 95.0 if block['on'] and fake.council_calls else 10.0}, 'week': {'p': 10.0}}
        eng = make_app(tmpdir(self), fake, cfg_extra=ON, plan_probe=probe)
        j = eng.submit(RISKY)
        eng.tick(max_seconds=0)
        eng.tick(max_seconds=0)
        self.assertEqual(len(fake.council_calls), 1)
        self.assertEqual(eng.status(j['job_id'])['state'], 'queued')
        block['on'] = False
        st = run_until(eng, job=j['job_id'])
        self.assertEqual(len(fake.council_calls), 3)                    # 3 Rollen, keine doppelt
        self.assertEqual(st['state'], 'waiting_approval')

    def test_revision_gets_its_own_council_round(self):
        fake = FakeClaude(WC_PLAN, wc_steps())
        eng = make_app(tmpdir(self), fake, cfg_extra=ON)
        j = eng.submit(RISKY)
        run_until(eng, job=j['job_id'])
        eng.revise(j['job_id'], 'Neustart erst nach dem Test von Apache', by='portal:andrew')
        st = run_until(eng, job=j['job_id'])
        self.assertEqual(st['council']['revision'], 2)
        self.assertEqual(len(fake.council_calls), 6)
        self.assertEqual(eng.council_metrics()['councils']['SECURITY']['rounds'], 2)

    def test_disabled_by_default(self):
        fake = FakeClaude(WC_PLAN, wc_steps())
        eng = make_app(tmpdir(self), fake)
        j = eng.submit(RISKY)
        run_until(eng, job=j['job_id'])
        self.assertEqual(fake.council_calls, [])


if __name__ == '__main__':
    unittest.main()
