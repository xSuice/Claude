"""AP1 Phase-1 acceptance tests: kimi_pro + nexum quota tracking, cost_usd, get_provider_quota().

Spec: KIMI_PRO_DIRECTOR_V2_PHASE_1_SPEC.md §1.4

AC1/AC2: verified via grep in test_default_limits_contains_new_providers
AC3: reserve kimi_pro with cost_usd succeeds
AC4: get_provider_quota('kimi_pro')['strategic_priority'] is True
AC5: 101st reserve on kimi_pro (calls_per_day=100) is rejected
AC6: existing test_v16_ledger.py still passes (run separately)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v16_fakes import tmpdir  # noqa: E402

from ledger import DEFAULT_LIMITS, Ledger  # noqa: E402


class AP1QuotaTests(unittest.TestCase):
    # --- AC1 / AC2: DEFAULT_LIMITS contains kimi_pro + nexum -----------------
    def test_default_limits_contains_kimi_pro(self):
        self.assertIn('kimi_pro', DEFAULT_LIMITS)
        kp = DEFAULT_LIMITS['kimi_pro']
        self.assertEqual(kp['calls_per_day'], 100)
        self.assertEqual(kp['tokens_per_day'], 5_000_000)
        self.assertAlmostEqual(kp['cost_usd_per_day'], 10.00)
        self.assertEqual(kp['max_concurrent'], 2)
        self.assertTrue(kp['strategic_priority'])

    def test_default_limits_contains_nexum(self):
        self.assertIn('nexum', DEFAULT_LIMITS)
        nx = DEFAULT_LIMITS['nexum']
        self.assertEqual(nx['calls_per_day'], 500)
        self.assertEqual(nx['tokens_per_day'], 10_000_000)
        self.assertAlmostEqual(nx['cost_usd_per_day'], 5.00)
        self.assertEqual(nx['max_concurrent'], 5)
        self.assertFalse(nx['strategic_priority'])

    # --- AC3: reserve('kimi_pro', tokens=1000, cost_usd=0.05) -> success -----
    def test_reserve_kimi_pro_with_cost_usd(self):
        t = tmpdir(self)
        led = Ledger(t / 's.db')
        rid, why = led.reserve('agent-router', 'jarvis', 'kimi_pro', 1000, cost_usd=0.05)
        self.assertIsNotNone(rid, f'expected reservation to succeed, got: {why!r}')
        self.assertEqual(why, '')

    # --- AC4: get_provider_quota('kimi_pro')['strategic_priority'] == True ---
    def test_get_provider_quota_kimi_pro_strategic(self):
        t = tmpdir(self)
        led = Ledger(t / 's.db')
        q = led.get_provider_quota('kimi_pro')
        self.assertEqual(q['resource'], 'kimi_pro')
        self.assertTrue(q['strategic_priority'])
        self.assertEqual(q['calls_limit'], 100)
        self.assertEqual(q['tokens_limit'], 5_000_000)
        self.assertAlmostEqual(q['cost_limit_usd'], 10.00)
        self.assertEqual(q['calls_used'], 0)
        self.assertEqual(q['tokens_used'], 0)
        self.assertAlmostEqual(q['cost_used_usd'], 0.0)
        self.assertAlmostEqual(q['remaining_pct'], 100.0)

    def test_get_provider_quota_nexum_not_strategic(self):
        t = tmpdir(self)
        led = Ledger(t / 's.db')
        q = led.get_provider_quota('nexum')
        self.assertEqual(q['resource'], 'nexum')
        self.assertFalse(q['strategic_priority'])
        self.assertEqual(q['calls_limit'], 500)

    # --- AC5: 101st kimi_pro reservation is rejected (calls_per_day=100) ----
    def test_kimi_pro_calls_per_day_quota_exceeded(self):
        t = tmpdir(self)
        # Tighten limits so test runs fast; keep everything else default-ish
        led = Ledger(t / 's.db', {
            'kimi_pro': {'calls_per_day': 100, 'tokens_per_day': 5_000_000,
                         'cost_usd_per_day': 10.00, 'max_concurrent': 200,
                         'strategic_priority': True}
        })
        results = []
        for i in range(101):
            rid, why = led.reserve(f'agent-{i % 4}', 'jarvis', 'kimi_pro', 100)
            results.append((rid, why))
        ok = sum(1 for rid, _ in results if rid is not None)
        self.assertEqual(ok, 100, f'expected exactly 100 accepted reservations, got {ok}')
        # The 101st reservation (index 100) must be rejected
        rid_101, why_101 = results[100]
        self.assertIsNone(rid_101, 'the 101st reservation must be rejected')
        self.assertIn('100', why_101)

    # --- cost_usd accumulation is tracked in quota ---
    def test_cost_usd_accumulates_in_quota(self):
        t = tmpdir(self)
        led = Ledger(t / 's.db')
        for i in range(5):
            rid, _ = led.reserve('agent-a', 'jarvis', 'kimi_pro', 1000, cost_usd=1.00)
            self.assertIsNotNone(rid)
            led.settle(rid, 1000, list_usd=1.00)
        q = led.get_provider_quota('kimi_pro')
        self.assertAlmostEqual(q['cost_used_usd'], 5.00)
        # 5 of 10 USD -> 50% used -> 50% remaining
        self.assertAlmostEqual(q['remaining_pct'], 50.0)

    # --- cost over limit is rejected ---
    def test_cost_usd_over_limit_rejected(self):
        t = tmpdir(self)
        led = Ledger(t / 's.db', {
            'kimi_pro': {'calls_per_day': 100, 'tokens_per_day': 5_000_000,
                         'cost_usd_per_day': 10.00, 'max_concurrent': 200,
                         'strategic_priority': True}
        })
        # Use 9.50 USD first (5 calls x 1.90)
        for _ in range(5):
            rid, _ = led.reserve('a', 'p', 'kimi_pro', 100, cost_usd=1.90)
            self.assertIsNotNone(rid)
            led.settle(rid, 100, list_usd=1.90)
        # A 1.00 USD call should still fit (9.50 + 1.00 = 10.50 > 10 but reservation
        # adds cost_usd as estimate before settle - depends on implementation; here
        # we assert that at least the hard ceiling blocks clearly over-budget calls)
        rid_big, why_big = led.reserve('a', 'p', 'kimi_pro', 100, cost_usd=5.00)
        self.assertIsNone(rid_big, f'over-budget reservation must fail, got rid={rid_big}')
        self.assertIn('cost', why_big.lower())

    # --- backward compatibility: existing call sites without cost_usd work ---
    def test_reserve_backward_compatible_no_cost_usd(self):
        t = tmpdir(self)
        led = Ledger(t / 's.db')
        rid, why = led.reserve('a', 'p', 'claude:sonnet', 100)
        self.assertIsNotNone(rid)
        rid2, why2 = led.reserve('a', 'p', 'helper:gemini', 100)
        self.assertIsNotNone(rid2)

    # --- unknown provider in get_provider_quota raises or returns safe default ---
    def test_get_provider_quota_unknown_resource_fail_closed(self):
        t = tmpdir(self)
        led = Ledger(t / 's.db')
        with self.assertRaises(KeyError):
            led.get_provider_quota('does_not_exist')


if __name__ == '__main__':
    unittest.main()
