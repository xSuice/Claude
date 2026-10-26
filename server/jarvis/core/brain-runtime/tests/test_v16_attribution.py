"""Herkunftskennzeichnung: alle drei Formen, Fehler, Offline/Budget, Nur-Weiterleitung, Retry, widersprüchliche Daten.
Reine Fälle laufen überall; Ende-zu-Ende-Fälle nur mit Sandbox (Linux), wie die übrigen V16-Tests."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v16_fakes import FakeClaude, WC_PLAN, make_app, run_until, tmpdir, wc_steps  # noqa: E402

import sandbox  # noqa: E402
from attribution import NOT_VERIFIED, attribute_direct_claude, attribute_job  # noqa: E402

LINUX = sys.platform == 'linux' and sandbox.available()


def st(**kw):
    base = {'id': 'j1', 'state': 'done', 'verdict': 'done', 'summary': '2/2 Ergebnisdateien bestanden die unabhängige Abnahme',
            'plan_source': 'claude', 'steps': [], 'calls': [], 'claude_calls': 0, 'helper_calls': 0}
    base.update(kw)
    return base


def call(sid, ok=1, model='sonnet'):
    return {'sid': sid, 'model': model, 'ok': ok, 'known': 1}


def evs(n):
    return [{'kind': 'claude_done'} for _ in range(n)]


class Pure(unittest.TestCase):
    def test_jarvis_only_from_template_and_local_steps(self):
        s = st(plan_source='template:3:exact', steps=[{'sid': 's1', 'kind': 'local', 'state': 'done'}])
        r = attribute_job(s, [])
        self.assertEqual(r['label'], 'Jarvis')
        self.assertTrue(r['line'].startswith('Jarvis: '), r['line'])
        self.assertIn('Status: abgeschlossen', r['line'])
        self.assertIn('Nachweis: j1', r['line'])
        self.assertNotIn('Claude', r['line'])

    def test_jarvis_plus_claude(self):
        s = st(steps=[{'sid': 's1', 'kind': 'claude', 'state': 'done'}], calls=[call('plan'), call('s1')], claude_calls=2)
        r = attribute_job(s, evs(2))
        self.assertEqual(r['label'], 'Jarvis + Claude')
        self.assertTrue(r['line'].startswith('Jarvis + Claude: '), r['line'])
        self.assertIn('Plan erstellt', r['line'])
        self.assertIn('unabhängige Abnahme', r['line'])

    def test_claude_only_needs_a_usage_record(self):
        r = attribute_direct_claude({'id': 'b-17', 'model': 'sonnet', 'ok': True, 'tokens_new': 1200})
        self.assertEqual(r['label'], 'Claude')
        self.assertTrue(r['line'].startswith('Claude: '), r['line'])
        self.assertNotIn('Jarvis', r['line'])
        bad = attribute_direct_claude({'id': 'b-18', 'model': 'sonnet', 'ok': True})
        self.assertIsNone(bad['label'])
        self.assertTrue(bad['line'].startswith(NOT_VERIFIED))

    def test_forwarding_alone_is_not_a_contribution(self):
        # Claude-Aufruf ok, aber weder lokaler Schritt noch Vorlage noch Abnahme: nur Weiterleitung
        s = st(state='failed', verdict='failed', summary='abgebrochen', steps=[{'sid': 's1', 'kind': 'claude', 'state': 'done'}],
               calls=[call('s1')], claude_calls=1)
        r = attribute_job(s, evs(1))
        self.assertIsNone(r['label'])
        self.assertIn('Weiterleitung', r['reason'])
        self.assertTrue(r['line'].startswith(NOT_VERIFIED))
        gone = attribute_direct_claude({'id': 'x', 'model': 'sonnet', 'ok': True, 'tokens_new': 5, 'jarvis_job': 'j1'})
        self.assertIsNone(gone['label'])

    def test_failed_claude_call_is_no_claude_contribution(self):
        s = st(state='failed', verdict='failed', steps=[{'sid': 's1', 'kind': 'claude', 'state': 'failed'}],
               calls=[call('s1', ok=0)], claude_calls=1, summary='0/1 Ergebnisdateien bestanden die unabhängige Abnahme')
        r = attribute_job(s, evs(1))
        self.assertIsNone(r['label'])
        self.assertIn('Status: fehlgeschlagen', r['line'])

    def test_open_job_has_no_final_label(self):
        for state in ('queued', 'running', 'waiting_approval', 'waiting_pc'):
            r = attribute_job(st(state=state, verdict=None), [])
            self.assertIsNone(r['label'], state)
            self.assertNotIn('Jarvis', r['line'])

    def test_inconsistent_data_is_not_verified(self):
        s = st(steps=[{'sid': 's1', 'kind': 'claude', 'state': 'done'}], calls=[call('s1')], claude_calls=1)
        self.assertIsNone(attribute_job(s, [])['label'])          # Aufruf ohne Ereignis
        s2 = st(steps=[{'sid': 's1', 'kind': 'claude', 'state': 'done'}], calls=[call('s1')], claude_calls=3)
        self.assertIsNone(attribute_job(s2, evs(1))['label'])     # Zähler passt nicht
        self.assertIsNone(attribute_job(st(), [])['label'])       # "abgeschlossen" ohne jeden Schritt
        self.assertIsNone(attribute_job(st(verdict='kaputt', state='kaputt'), [])['label'])

    def test_partial_and_cancelled_status_words(self):
        steps = [{'sid': 's1', 'kind': 'local', 'state': 'done'}]
        self.assertIn('Status: teilweise', attribute_job(st(state='partial', verdict='partial', steps=steps), [])['line'])
        self.assertIn('Status: fehlgeschlagen', attribute_job(st(state='cancelled', verdict='cancelled', steps=steps), [])['line'])


@unittest.skipUnless(LINUX, 'needs Linux with a sandbox backend')
class EndToEnd(unittest.TestCase):
    def test_real_job_is_labelled_from_its_own_log(self):
        t = tmpdir(self)
        eng = make_app(t, FakeClaude(WC_PLAN, wc_steps()))
        j = eng.submit('Erstelle ein Python-Werkzeug, das Wörter zählt, mit Tests', client_id='attrib-test-0001')
        s = run_until(eng, job=j['job_id'])
        self.assertEqual(s['state'], 'done', s)
        a = s['attribution']
        self.assertEqual(a['label'], 'Jarvis + Claude', a)
        self.assertEqual(a['ref'], j['job_id'])
        events = [e for e in eng.events(j['job_id'], 0, 1000) if e['kind'] == 'attribution']
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['text'], a['line'])
        self.assertTrue((Path(s['results']) / 'BERICHT.md').read_text().rstrip().endswith(a['line']))
        self.assertIn('python.unittest', str([x['capability'] for x in s['steps']]))   # lokaler Werkzeugschritt belegt

    def test_retry_after_failed_acceptance_still_labelled_correctly(self):
        t = tmpdir(self)
        eng = make_app(t, FakeClaude(WC_PLAN, wc_steps(bad_first=True)))
        j = eng.submit('Erstelle ein Python-Werkzeug, das Wörter zählt, mit Tests', client_id='attrib-test-0002')
        s = run_until(eng, job=j['job_id'])
        self.assertEqual(s['state'], 'done', s)
        self.assertGreaterEqual(s['fix_rounds'], 1)
        self.assertEqual(s['attribution']['label'], 'Jarvis + Claude')

    def test_budget_stop_never_claims_more_than_proven(self):
        t = tmpdir(self)
        eng = make_app(t, FakeClaude(WC_PLAN, wc_steps()), job_defaults={'claude_calls': 2})
        j = eng.submit('Wortzähler mit Tests')
        s = run_until(eng, job=j['job_id'])
        a = s['attribution']
        self.assertIn(s['state'], ('partial', 'failed'))
        self.assertIn(a['status'], ('teilweise', 'fehlgeschlagen'))
        if a['label']:
            self.assertIn(a['label'], ('Jarvis', 'Jarvis + Claude'))
        else:
            self.assertTrue(a['line'].startswith(NOT_VERIFIED))

    def test_offline_claude_defers_and_gets_no_label(self):
        t = tmpdir(self)
        fake = FakeClaude(WC_PLAN, wc_steps())
        eng = make_app(t, fake, limits={'claude': {'calls_per_day': 0}})
        j = eng.submit('Wortzähler mit Tests')
        for _ in range(4):
            eng.tick(max_seconds=2)
        s = eng.status(j['job_id'])
        self.assertNotIn(s['state'], ('done',))
        self.assertEqual(fake.calls, [])
        self.assertIsNone(s['attribution']['label'])
        self.assertNotIn('Claude:', s['attribution']['line'])

    def test_cancelled_job_reports_failure_not_success(self):
        t = tmpdir(self)
        eng = make_app(t, FakeClaude(WC_PLAN, wc_steps()))
        j = eng.submit('Wortzähler')
        eng.cancel(j['job_id'])
        eng.tick(max_seconds=1)
        a = eng.status(j['job_id'])['attribution']
        self.assertIsNone(a['label'])
        self.assertIn('Status: fehlgeschlagen', a['line'])

    def test_repeat_job_from_template_still_shows_claude_if_claude_wrote_content(self):
        t = tmpdir(self)
        fake = FakeClaude(WC_PLAN, wc_steps())
        eng = make_app(t, fake)
        req = 'Erstelle ein Python-Werkzeug, das Wörter zählt, mit Tests'
        run_until(eng, job=eng.submit(req, client_id='first-attr-0001')['job_id'])
        b = eng.submit(req, client_id='second-attr-0002')
        s = run_until(eng, job=b['job_id'])
        self.assertTrue(s['plan_source'].startswith('template:'))
        self.assertEqual(s['attribution']['label'], 'Jarvis + Claude')
        self.assertNotIn('Plan erstellt', s['attribution']['line'])   # Plan kam aus der Vorlage, nicht von Claude


if __name__ == '__main__':
    unittest.main()
