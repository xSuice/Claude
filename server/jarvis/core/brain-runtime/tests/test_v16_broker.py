"""Capability-Broker + Not-Aus-Stufen: Policy außerhalb des Prompts, Freigabe an Revision+Schritt+Parameter gebunden und
einmalig, Audit je Schritt mit redigierten Parametern, SOFT/EXEC/HARD ohne LLM."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v16_fakes import FakeClaude, WC_PLAN, make_app, run_until, tmpdir, wc_steps  # noqa: E402

import broker  # noqa: E402
import sandbox  # noqa: E402

LINUX = sys.platform == 'linux' and sandbox.available()


class Policy(unittest.TestCase):
    def d(self, cap, **kw):
        base = dict(kill=None, job_active=True, revision_ok=True, data_class='internal', budget_ok=True, approved=False)
        return broker.decide(cap, **{**base, **kw})['decision']

    def test_order_of_checks(self):
        self.assertEqual(self.d('sandbox.exec'), 'allow')
        self.assertEqual(self.d('sandbox.exec', kill='exec'), 'deny')
        self.assertEqual(self.d('sandbox.exec', kill='soft'), 'allow')        # SOFT stoppt nur neue Aufträge
        self.assertEqual(self.d('sandbox.exec', revision_ok=False), 'deny')
        self.assertEqual(self.d('git.push'), 'deny')                           # Ziel-Fähigkeit ohne Executor
        self.assertEqual(self.d('sandbox.exec', budget_ok=False), 'deny')
        self.assertEqual(self.d('sandbox.exec', secret_refs=['github/jarvis-bot']), 'deny')

    def test_conditional_needs_approval_unless_public(self):
        self.assertEqual(self.d('sandbox.exec_networked', data_class='public'), 'allow')
        self.assertEqual(self.d('sandbox.exec_networked'), 'approval')
        self.assertEqual(self.d('sandbox.exec_networked', approved=True), 'allow')
        self.assertEqual(self.d('memory.propose_write', data_class='public'), 'approval')   # immer Freigabe

    def test_approval_is_bound_to_params(self):
        a = broker.params_hash('j1', 1, 's1', 'sandbox.exec_networked', {'args': {'url': 'a'}})
        self.assertNotEqual(a, broker.params_hash('j1', 1, 's1', 'sandbox.exec_networked', {'args': {'url': 'b'}}))
        self.assertNotEqual(a, broker.params_hash('j1', 2, 's1', 'sandbox.exec_networked', {'args': {'url': 'a'}}))

    def test_kill_levels_from_file(self):
        d = Path(tmpdir(self))
        self.assertIsNone(broker.kill_level(d / 'KILL'))
        (d / 'KILL').write_text('2026-10-28 Not-Aus')                    # altes Format bleibt "alles stoppen"
        self.assertEqual(broker.kill_level(d / 'KILL'), 'exec')
        (d / 'KILL').write_text('soft\n')
        self.assertEqual(broker.kill_level(d / 'KILL'), 'soft')


@unittest.skipUnless(LINUX, 'needs Linux with a sandbox backend')
class InEngine(unittest.TestCase):
    def test_every_step_is_audited_with_decision(self):
        eng = make_app(tmpdir(self), FakeClaude(WC_PLAN, wc_steps()))
        j = eng.submit('Wortzähler mit Tests')
        st = run_until(eng, job=j['job_id'])
        self.assertEqual(st['state'], 'done', st['summary'])
        au = eng.audit(j['job_id'])['audit']
        self.assertEqual(len(au), len(st['steps']))
        self.assertTrue(all(a['decision'] == 'allow' and a['result'] for a in au))
        self.assertEqual({a['capability'] for a in au}, {'llm.worker', 'sandbox.exec'})

    def test_soft_stop_finishes_running_but_starts_nothing_new(self):
        eng = make_app(tmpdir(self), FakeClaude(WC_PLAN, wc_steps()))
        j1 = eng.submit('Wortzähler mit Tests')
        eng.tick(max_seconds=0)                                             # j1 läuft an (geplant)
        (eng.brain.db_path.parent / 'KILL').write_text('soft')
        j2 = None
        try:
            j2 = eng.submit('Zweiter Auftrag: Wortzähler mit Tests und README')
        except PermissionError:
            pass                                                           # neue Aufträge bei Not-Aus abgelehnt
        st = run_until(eng, job=j1['job_id'])
        self.assertEqual(st['state'], 'done', st['summary'])
        if j2:
            self.assertEqual(eng.status(j2['job_id'])['state'], 'queued')

    def test_exec_stop_runs_nothing(self):
        fake = FakeClaude(WC_PLAN, wc_steps())
        eng = make_app(tmpdir(self), fake)
        j = eng.submit('Wortzähler mit Tests')
        (eng.brain.db_path.parent / 'KILL').write_text('exec')
        self.assertIn('kill switch', eng.tick(max_seconds=0)['idle'])
        self.assertEqual(fake.calls, [])
        self.assertEqual(eng.status(j['job_id'])['state'], 'queued')

    def test_approval_flow_is_single_use_and_revision_bound(self):
        fake = FakeClaude(WC_PLAN, wc_steps())
        eng = make_app(tmpdir(self), fake)
        j = eng.submit('Wortzähler mit Tests')
        orig = broker.CATALOG['llm.worker']['approval']
        broker.CATALOG['llm.worker']['approval'] = 'approval'               # Testfall: Worker-Schritt braucht Freigabe
        try:
            st = run_until(eng, job=j['job_id'])
            self.assertEqual(st['state'], 'waiting_approval')
            pend = eng.audit(j['job_id'])['pending_approvals']
            self.assertEqual(len(pend), 1)
            eng.approve(j['job_id'], by='portal:andrew')
            st = run_until(eng, job=j['job_id'], rounds=3)
            with eng._conn() as c:
                states = [r[0] for r in c.execute('SELECT state FROM cap_approvals WHERE job_id=?', (j['job_id'],))]
            self.assertIn('used', states)                                   # verbraucht, nicht wiederverwendbar
            decisions = [a['decision'] for a in eng.audit(j['job_id'])['audit']]
            self.assertIn('approval', decisions)
            self.assertIn('allow', decisions)
        finally:
            broker.CATALOG['llm.worker']['approval'] = orig

    def test_params_are_redacted_in_audit(self):
        eng = make_app(tmpdir(self), FakeClaude(WC_PLAN, wc_steps()))
        j = eng.submit('Wortzähler mit Tests')
        run_until(eng, job=j['job_id'])
        aid = eng._audit(job_id=j['job_id'], revision=1, capability='sandbox.exec', decision='allow',
                         params={'args': {'token': 'ghp_' + 'A' * 36}})
        row = [a for a in eng.audit(j['job_id'])['audit'] if a['id'] == aid][0]
        self.assertNotIn('A' * 36, row['params'])


if __name__ == '__main__':
    unittest.main()
