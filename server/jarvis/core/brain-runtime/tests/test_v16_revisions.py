"""V16 Auftragsrevisionen: Task-ID bleibt, Revision steigt atomar; alte Revisionen duerfen keine Ergebnisse, Seiteneffekte
oder Abschluesse mehr schreiben (Fencing); neustartfest; Geheimnis-/Urheberregeln wie beim Anlegen. Linux (sandbox) only."""
import json
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v16_fakes import FakeClaude, WC_PLAN, make_app, run_until, tmpdir, wc_steps  # noqa: E402

import sandbox  # noqa: E402
from taskengine import make_tar  # noqa: E402

LINUX = sys.platform == 'linux' and sandbox.available()
BY = 'portal:andrew'


@unittest.skipUnless(LINUX, 'needs Linux with a sandbox backend')
class Revisions(unittest.TestCase):
    def test_submit_starts_at_revision_1_with_history_row(self):
        eng = make_app(tmpdir(self), FakeClaude(WC_PLAN, wc_steps()))
        j = eng.submit('Wortzähler mit Tests')
        st = eng.status(j['job_id'])
        self.assertEqual(st['revision'], 1)
        self.assertEqual([r['revision'] for r in st['revisions']], [1])

    def test_revise_before_planning_keeps_id_and_bumps_revision(self):
        fake = FakeClaude(WC_PLAN, wc_steps())
        eng = make_app(tmpdir(self), fake)
        j = eng.submit('Wortzähler mit Tests')
        r = eng.revise(j['job_id'], 'Bitte zusätzlich eine Hilfe mit --help ausgeben', by=BY)
        self.assertEqual((r['job_id'], r['revision'], r['state']), (j['job_id'], 2, 'queued'))
        st = run_until(eng, job=j['job_id'])
        self.assertEqual(st['state'], 'done', st['summary'])
        self.assertEqual(st['revision'], 2)
        self.assertEqual(fake.planning_calls, 1)                       # no wasted planning for rev 1
        self.assertIn('--help', fake.calls[0]['prompt'])               # the planner saw the change
        revs = st['revisions']
        self.assertEqual([(x['revision'], x['parent']) for x in revs], [(1, None), (2, 1)])
        self.assertEqual(revs[1]['by'], BY)
        self.assertIn('revised', [e['kind'] for e in eng.events(j['job_id'])])

    def test_revise_mid_run_replans_and_snapshots_superseded_steps(self):
        fake = FakeClaude(WC_PLAN, wc_steps())
        eng = make_app(tmpdir(self), fake)
        j = eng.submit('Wortzähler mit Tests')
        eng.tick(max_seconds=0)   # plan (rev 1)
        eng.tick(max_seconds=0)   # s1 done
        r = eng.revise(j['job_id'], 'README zusätzlich auf Englisch', by=BY)
        self.assertEqual(r['superseded_steps'], 2)   # s2+s3 offen, s1 war schon erledigt
        st = run_until(eng, job=j['job_id'])
        self.assertEqual((st['state'], st['revision']), ('done', 2), st['summary'])
        self.assertEqual(fake.planning_calls, 2)
        with eng.brain.connection() as c:
            snap = json.loads(c.execute('SELECT superseded_steps FROM job_revisions WHERE job_id=? AND revision=1',
                                        (j['job_id'],)).fetchone()[0])
            revs = {r[0] for r in c.execute('SELECT DISTINCT revision FROM job_steps WHERE job_id=?', (j['job_id'],))}
        self.assertEqual({s['sid']: s['state'] for s in snap}['s1'], 'done')   # history kept, not overwritten
        self.assertEqual(revs, {2})                                             # only rev-2 steps are live

    def test_stale_executor_result_is_fenced_after_revision(self):
        steps = wc_steps()
        box = {}
        orig = steps['Code und Tests schreiben']

        def code(cwd, prompt, n):
            out = orig(cwd, prompt, n)
            if n == 1:   # the owner changes the order while this step (rev 1) is still running
                box['r'] = box['eng'].revise(box['job'], 'Zähle zusätzlich Zeilen', by=BY)
            return out
        steps['Code und Tests schreiben'] = code
        fake = FakeClaude(WC_PLAN, steps)
        eng = make_app(tmpdir(self), fake)
        j = eng.submit('Wortzähler mit Tests')
        box.update(eng=eng, job=j['job_id'])
        eng.tick(max_seconds=0)   # plan
        eng.tick(max_seconds=0)   # s1 runs, revision happens inside
        evs = eng.events(j['job_id'])
        self.assertIn('superseded', [e['kind'] for e in evs])
        self.assertNotIn('step_done', [e['kind'] for e in evs])            # rev-1 result was not persisted
        self.assertEqual(eng.status(j['job_id'])['state'], 'queued')       # waits for re-planning of rev 2
        st = run_until(eng, job=j['job_id'])
        self.assertEqual((st['state'], st['revision']), ('done', 2), st['summary'])

    def test_finalize_of_old_revision_writes_no_verdict(self):
        eng = make_app(tmpdir(self), FakeClaude(WC_PLAN, wc_steps()))
        j = eng.submit('Wortzähler mit Tests')
        eng.tick(max_seconds=0)
        stale = eng._job(j['job_id'])
        eng.revise(j['job_id'], 'Andere Ausgabeform', by=BY)
        r = eng._finalize(stale)
        self.assertEqual(r.get('why'), 'superseded')
        st = eng.status(j['job_id'])
        self.assertEqual((st['state'], st['verdict']), ('queued', None))

    def test_revision_survives_restart(self):
        t = tmpdir(self)
        fake = FakeClaude(WC_PLAN, wc_steps())
        eng = make_app(t, fake)
        j = eng.submit('Wortzähler mit Tests')
        eng.tick(max_seconds=0)
        eng.revise(j['job_id'], 'Ergänze eine Beispieldatei', by=BY)
        eng2 = make_app(t, fake, registry=eng.reg)   # "Neustart"
        self.assertEqual(eng2.status(j['job_id'])['revision'], 2)
        st = run_until(eng2, job=j['job_id'])
        self.assertEqual((st['state'], st['revision']), ('done', 2), st['summary'])

    def test_concurrent_revisions_compare_and_set(self):
        eng = make_app(tmpdir(self), FakeClaude(WC_PLAN, wc_steps()))
        j = eng.submit('Wortzähler mit Tests')
        ok, err = [], []

        def go(i):
            try:
                ok.append(eng.revise(j['job_id'], f'Änderung Nummer {i}', by=BY, expected_revision=1))
            except ValueError as e:
                err.append(str(e))
        ths = [threading.Thread(target=go, args=(i,)) for i in range(5)]
        [x.start() for x in ths]
        [x.join() for x in ths]
        self.assertEqual(len(ok), 1, (ok, err))
        self.assertEqual(len(err), 4)
        self.assertEqual(eng.status(j['job_id'])['revision'], 2)

    def test_rules_final_secret_origin(self):
        eng = make_app(tmpdir(self), FakeClaude(WC_PLAN, wc_steps()))
        j = eng.submit('Wortzähler mit Tests')
        with self.assertRaises(PermissionError):
            eng.revise(j['job_id'], 'nimm das Passwort: hunter2hunter2 und api_key=sk-abcdefghijklmnopqrstuvwx', by=BY)
        with self.assertRaises(PermissionError):
            eng.revise(j['job_id'], 'Änderung ohne Urheber', by='irgendwer')
        with self.assertRaises(ValueError):
            eng.revise(j['job_id'], 'x', by=BY)
        self.assertEqual(eng.status(j['job_id'])['revision'], 1)
        eng.cancel(j['job_id'])
        with self.assertRaises(ValueError):
            eng.revise(j['job_id'], 'zu spät geändert', by=BY)

    def test_new_effects_from_change_are_classified(self):
        eng = make_app(tmpdir(self), FakeClaude(WC_PLAN, wc_steps()))
        j = eng.submit('Wortzähler mit Tests')
        eng.revise(j['job_id'], 'und danach sudo systemctl restart nginx ausführen', by=BY)
        with eng.brain.connection() as c:
            spec = json.loads(c.execute('SELECT spec FROM jobs WHERE id=?', (j['job_id'],)).fetchone()[0])
        self.assertIn('privileged', spec['effects'])
        self.assertTrue(spec['plan_approval'])          # escalated risk needs a plan approval again

    def test_pc_result_of_superseded_revision_is_rejected_before_extract(self):
        eng = make_app(tmpdir(self), FakeClaude(WC_PLAN, wc_steps()))
        j = eng.submit('Wortzähler mit Tests')
        eng.tick(max_seconds=0)
        with eng.brain.connection(True) as c:   # pretend s2 is a PC step leased by the worker under rev 1
            c.execute("UPDATE job_steps SET kind='pc', state='running' WHERE job_id=? AND sid='s2'", (j['job_id'],))
            c.execute("UPDATE jobs SET lease_owner='pc:win', lease_until=9999999999 WHERE id=?", (j['job_id'],))
        eng.revise(j['job_id'], 'Andere Testdaten verwenden', by=BY)
        st = eng.status(j['job_id'])
        tmp = tmpdir(self)
        (tmp / 'EVIL.txt').write_text('late result of an old revision')
        with self.assertRaises(ValueError):
            eng.pc_complete(j['job_id'], 's2', True, 'fertig', make_tar(tmp))
        self.assertFalse((Path(eng._job(j['job_id'])['workspace']) / 'EVIL.txt').exists())
        self.assertEqual(st['revision'], 2)
        with eng.brain.connection() as c:   # the PC lease was released so rev 2 can be planned at once
            self.assertIsNone(c.execute('SELECT lease_owner FROM jobs WHERE id=?', (j['job_id'],)).fetchone()[0])


if __name__ == '__main__':
    unittest.main()
