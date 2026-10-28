"""Memory Distiller (Knowledge-Vertrag): nur nach bestandener Abnahme, kein Chat-Dump, Herkunft/Evidenz, Dedupe,
Widerspruch zur Prüfung, Vault-Schreiben nur nach Freigabe mit bekanntem Urheber, nie überschreiben."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v16_fakes import FakeClaude, WC_PLAN, make_app, run_until, tmpdir, wc_steps  # noqa: E402

import distiller  # noqa: E402
import sandbox  # noqa: E402

LINUX = sys.platform == 'linux' and sandbox.available()


class Pure(unittest.TestCase):
    JOB = {'id': 'j20261028-aaaaaa', 'revision': 2, 'verdict': 'done', 'fix_rounds': 1, 'request': 'GEHEIMER CHATTEXT xyz',
           'spec': {'data_class': 'internal'}, 'results': '/r'}
    PLAN = {'task_type': 'coding.python_cli', 'steps': [{'id': 's1', 'title': 'Code schreiben'}, {'id': 's2', 'title': 'Tests', 'capability': 'python.unittest'}]}
    ACC = {'ok': True, 'deliverables': [{'ok': True}, {'ok': True}]}
    EVS = [{'id': 5, 'kind': 'step_failed', 'text': 'Schritt s2 gescheitert: 1 Test rot'}, {'id': 9, 'kind': 'finished', 'text': 'done'}]

    def test_only_after_passed_acceptance(self):
        self.assertEqual(distiller.extract({**self.JOB, 'verdict': 'partial'}, self.PLAN, self.ACC, self.EVS, None), [])
        self.assertEqual(distiller.extract(self.JOB, self.PLAN, {**self.ACC, 'ok': False}, self.EVS, None), [])

    def test_candidates_carry_evidence_and_no_chat_text(self):
        c = distiller.extract(self.JOB, self.PLAN, self.ACC, self.EVS, {'council': 'DEV', 'constraints': ['Tests zuerst'], 'dissent': ['x']})
        self.assertEqual([x['kind'] for x in c], ['procedure', 'lesson', 'decision'])
        for x in c:
            self.assertNotIn('GEHEIMER CHATTEXT', x['body'])
            self.assertEqual(x['evidence']['job'], 'j20261028-aaaaaa')
            self.assertEqual(x['evidence']['revision'], 2)
            self.assertEqual(x['evidence']['acceptance'], {'ok': True, 'passed': 2, 'total': 2})
            self.assertIn(5, x['evidence']['events'])

    def test_dedupe_and_conflict(self):
        c = distiller.extract(self.JOB, self.PLAN, self.ACC, self.EVS, None)[0]
        self.assertEqual(distiller.classify(c, [])[0], 'proposed')
        self.assertEqual(distiller.classify(c, [{'id': 1, **c, 'state': 'written'}]), ('duplicate', 1))
        other = {'id': 2, 'topic': c['topic'], 'body': 'völlig anderer Ablauf mit Docker Compose und Ansible', 'fingerprint': 'f', 'state': 'written'}
        self.assertEqual(distiller.classify(c, [other]), ('conflict', 2))

    def test_note_is_never_overwritten(self):
        d = tmpdir(self)
        c = {**distiller.extract(self.JOB, self.PLAN, self.ACC, self.EVS, None)[0], 'id': 7}
        p = distiller.write_note(Path(d), c, 'portal:andrew')
        text = p.read_text(encoding='utf-8')
        self.assertIn('source: jarvis-v16', text)
        self.assertIn('job: j20261028-aaaaaa', text)
        with self.assertRaises(FileExistsError):
            distiller.write_note(Path(d), c, 'portal:andrew')


@unittest.skipUnless(LINUX, 'needs Linux with a sandbox backend')
class InEngine(unittest.TestCase):
    def test_done_job_creates_review_queue_and_approval_writes_vault(self):
        d = tmpdir(self)
        vault = Path(d) / 'vault'
        eng = make_app(Path(d) / 'app', FakeClaude(WC_PLAN, wc_steps()), cfg_extra={'knowledge_dir': str(vault)})
        j = eng.submit('Wortzähler mit Tests')
        st = run_until(eng, job=j['job_id'])
        self.assertEqual(st['state'], 'done', st['summary'])
        q = eng.knowledge('list')
        self.assertGreaterEqual(q['counts'].get('proposed', 0), 1)
        self.assertFalse(vault.exists())                                  # nichts ohne Freigabe
        cid = next(c['id'] for c in q['candidates'] if c['state'] == 'proposed')
        with self.assertRaises(PermissionError):
            eng.knowledge('approve', cid, by='')                          # kein unbekannter Urheber
        r = eng.knowledge('approve', cid, by='portal:andrew')
        self.assertEqual(r['state'], 'written')
        self.assertTrue(Path(r['note']).is_file())
        with self.assertRaises(PermissionError):
            eng.knowledge('approve', cid, by='portal:andrew')             # nicht doppelt
        self.assertIn('knowledge_written', [e['kind'] for e in eng.events(j['job_id'])])
        # gleicher Auftrag noch einmal -> Duplikat, keine zweite offene Notiz
        j2 = eng.submit('Wortzähler mit Tests, zweiter Lauf')
        self.assertNotEqual(j2['job_id'], j['job_id'])
        run_until(eng, job=j2['job_id'])
        new = [c for c in eng.knowledge('list')['candidates'] if c['job_id'] == j2['job_id']]
        self.assertTrue(new and all(c['state'] == 'duplicate' for c in new if c['kind'] == 'procedure'), json.dumps(new)[:400])


if __name__ == '__main__':
    unittest.main()
