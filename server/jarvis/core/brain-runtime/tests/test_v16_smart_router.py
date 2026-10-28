"""Smart Router (Router-Vertrag): harte Filter, gewichteter Score, Ausweichen bei Störung, keine erfundenen Quoten,
Shadow ohne Wirkung, Canary deterministisch und nur Claude-Modelle, rückwirkende Shadow-Eval ohne Policy-Verstoß."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v16_fakes import FakeClaude, WC_PLAN, make_app, run_until, tmpdir, wc_steps  # noqa: E402

import sandbox  # noqa: E402
import smart_policy as sp  # noqa: E402

LINUX = sys.platform == 'linux' and sandbox.available()


def cat(nexum=True):
    return sp.catalog({}, 'qwen-test' if nexum else None)


def dec(text='x', data='internal', effects=(), cx='routine', planning=False, tools=True, metrics=None, quota=None, aliases=None):
    return sp.decide(text=text, spec={'data_class': data, 'effects': list(effects)}, complexity=cx, planning=planning,
                     needs_tools=tools, aliases=aliases or cat(), metrics=metrics or {}, quota=quota or {})


class Policy(unittest.TestCase):
    def test_unconfigured_providers_are_excluded_not_invented(self):
        d = dec()
        for a in ('kimi-main', 'kimi-interactive', 'local-fast', 'fallback-diverse'):
            self.assertEqual(d['excluded'][a], 'nicht konfiguriert')

    def test_private_and_internal_never_reach_untrusted(self):
        for data in ('internal', 'private'):
            d = dec(data=data)
            self.assertIn('Datenschutz', d['excluded']['bulk-cheap-untrusted'])
            self.assertEqual(sp.violations(d, {'data_class': data}, cat()), [])

    def test_public_bulk_may_use_nexum_but_not_with_risky_effects(self):
        d = dec(data='public')
        self.assertIn('bulk-cheap-untrusted', d['candidates'])
        d2 = dec(data='public', effects=['send'])
        self.assertIn('riskante Wirkung', d2['excluded']['bulk-cheap-untrusted'])

    def test_complexity_moves_model_up(self):
        self.assertEqual(dec(cx='routine')['alias'], 'claude-haiku')
        self.assertEqual(dec(cx='strategic')['alias'], 'claude-sonnet')
        self.assertEqual(dec(cx='critical')['alias'], 'claude-opus')
        self.assertNotEqual(dec(cx='routine', planning=True)['alias'], 'claude-haiku')   # Planung braucht Qualität

    def test_broken_provider_is_avoided_automatically(self):
        m = {'claude-haiku': {'calls': 10, 'ok': 7, 'recent_fail_streak': 3, 'avg_s': 10, 'avg_usd': 0.01}}
        d = dec(metrics=m)
        self.assertIn('gestört', d['excluded']['claude-haiku'])
        self.assertIsNotNone(d['alias'])
        self.assertNotEqual(d['alias'], 'claude-haiku')

    def test_exhausted_quota_falls_back_or_fails_closed(self):
        q = {'anthropic-plan': {'blocked': True}}
        self.assertEqual(dec(data='public', quota=q)['alias'], 'bulk-cheap-untrusted')     # öffentlich: Ausweichen erlaubt
        d = dec(data='private', quota=q)
        self.assertIsNone(d['alias'])                                                      # privat: fail-closed
        self.assertIn('fail-closed', d['reason'])

    def test_missing_measurements_are_marked_estimated(self):
        d = dec()
        self.assertIn('quota', d['candidates']['claude-haiku']['estimated'])
        self.assertIn('reliability', d['candidates']['claude-haiku']['estimated'])
        d2 = dec(quota={'anthropic-plan': {'remaining': 0.6}},
                 metrics={'claude-haiku': {'calls': 9, 'ok': 9, 'avg_s': 9, 'avg_usd': 0.004}})
        self.assertEqual(d2['candidates']['claude-haiku']['estimated'], [])

    def test_weights_sum_to_one_and_canary_is_deterministic(self):
        self.assertAlmostEqual(sum(sp.WEIGHTS.values()), 1.0)
        self.assertEqual(sp.in_canary('j1', 30), sp.in_canary('j1', 30))
        share = sum(sp.in_canary(f'j{i}', 20) for i in range(2000)) / 2000
        self.assertTrue(0.15 < share < 0.25, share)
        self.assertFalse(sp.in_canary('j1', 0))


@unittest.skipUnless(LINUX, 'needs Linux with a sandbox backend')
class InEngine(unittest.TestCase):
    def test_shadow_logs_but_changes_nothing(self):
        fake = FakeClaude(WC_PLAN, wc_steps())
        eng = make_app(tmpdir(self), fake)
        j = eng.submit('Wortzähler mit Tests')
        st = run_until(eng, job=j['job_id'])
        self.assertEqual(st['state'], 'done', st['summary'])
        rep = eng.router_report()
        self.assertEqual(rep['mode'], 'shadow')
        self.assertGreater(rep['decisions'], 0)
        self.assertEqual(rep['applied'], 0)
        self.assertEqual(rep['violation_count'], 0)
        self.assertIn(rep['budgets']['moonshot']['confidence'], ('not_connected',))
        self.assertIsNone(rep['budgets']['moonshot']['remaining'])

    def test_active_mode_applies_only_claude_models_and_respects_manual(self):
        fake = FakeClaude(WC_PLAN, wc_steps())
        eng = make_app(tmpdir(self), fake, cfg_extra={'router': {'mode': 'active'}})
        j = eng.submit('Wortzähler mit Tests')
        run_until(eng, job=j['job_id'])
        self.assertTrue(all(c['model'] in ('haiku', 'sonnet', 'opus') for c in fake.calls))
        fake2 = FakeClaude(WC_PLAN, wc_steps())
        eng2 = make_app(tmpdir(self), fake2, cfg_extra={'router': {'mode': 'active'}})
        j2 = eng2.submit('Wortzähler mit Tests', options={'model': 'opus'})
        run_until(eng2, job=j2['job_id'])
        self.assertTrue(all(c['model'] == 'opus' for c in fake2.calls if not c['council']))

    def test_quota_rejections_are_not_model_failures(self):
        fake = FakeClaude(WC_PLAN, wc_steps())
        eng = make_app(tmpdir(self), fake)
        j = eng.submit('Wortzähler mit Tests')
        run_until(eng, job=j['job_id'])
        with eng._conn(True) as c:
            for i in range(3):
                c.execute("INSERT INTO job_calls(job_id,sid,model,ts,ms,ok,turns,known,tokens_in,cache_write,cache_read,tokens_out,list_usd) "
                          "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (j['job_id'], f'q{i}', 'sonnet', int(eng.clock()), 1000, 0, 1, 1, 0, 0, 0, 0, 0))
        for i in range(3):
            eng.event(j['job_id'], 'claude_done', f"Schritt q{i}: sonnet, 1 s, neu 0 / Cache 0 Token, Ergebnis Fehler: success You've hit your weekly limit")
        m = eng._route_metrics()['claude-sonnet']
        self.assertEqual(m['quota_rejections'], 3)
        self.assertEqual(m['recent_fail_streak'], 0)
        self.assertEqual(m['ok'], m['calls'])

    def test_backtest_runs_on_history_without_violations(self):
        fake = FakeClaude(WC_PLAN, wc_steps())
        eng = make_app(tmpdir(self), fake)
        for req in ('Wortzähler mit Tests', 'Wortzähler mit Tests und Architektur-Konzept'):
            run_until(eng, job=eng.submit(req)['job_id'])
        bt = eng.router_backtest()
        self.assertGreater(bt['calls'], 0)
        self.assertEqual(bt['violations'], 0)
        self.assertIsNotNone(bt['agreement'])
        json.dumps(bt)


if __name__ == '__main__':
    unittest.main()
