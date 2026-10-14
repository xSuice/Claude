"""V16 global ledger: hard limits under threads AND separate processes, restarts, stale reservations,
plan quota guard, unit separation (tokens vs list price)."""
import multiprocessing as mp
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v16_fakes import tmpdir  # noqa: E402

from ledger import Ledger  # noqa: E402


def _proc_reserve(db, n, q):
    led = Ledger(Path(db), {'claude': {'calls_per_day': 7, 'identity_calls_per_day': 100, 'max_concurrent': 100}})
    got = 0
    for _ in range(n):
        rid, _why = led.reserve('person-a' if n % 2 else 'person-b', 'jarvis', 'claude:sonnet', 100)
        if rid:
            got += 1
            led.settle(rid, 50)
    q.put(got)


class LedgerTests(unittest.TestCase):
    def test_threads_never_exceed(self):
        t = tmpdir(self)
        led = Ledger(t / 's.db', {'claude': {'calls_per_day': 5, 'max_concurrent': 100}})
        got = []

        def go():
            rid, _ = led.reserve('a', 'p', 'claude:sonnet', 10)
            if rid:
                got.append(rid)
        ths = [threading.Thread(target=go) for _ in range(40)]
        [x.start() for x in ths]
        [x.join() for x in ths]
        self.assertEqual(len(got), 5)

    @unittest.skipUnless(sys.platform == 'linux', 'fork based')
    def test_processes_and_two_identities_share_one_limit(self):
        t = tmpdir(self)
        Ledger(t / 's.db')
        q = mp.Queue()
        ps = [mp.Process(target=_proc_reserve, args=(str(t / 's.db'), 5 + i % 2, q)) for i in range(6)]
        [p.start() for p in ps]
        [p.join() for p in ps]
        self.assertEqual(sum(q.get() for _ in ps), 7)

    def test_token_limit_and_settle(self):
        t = tmpdir(self)
        led = Ledger(t / 's.db', {'claude': {'tokens_per_day': 1000, 'max_concurrent': 10}})
        r1, _ = led.reserve('a', 'p', 'claude', 800)
        r2, why = led.reserve('a', 'p', 'claude', 300)
        self.assertIsNone(r2)
        self.assertIn('token', why)
        led.settle(r1, 200)                    # real usage lower -> budget comes back
        r3, _ = led.reserve('a', 'p', 'claude', 300)
        self.assertIsNotNone(r3)

    def test_unknown_usage_and_stale_reservations_stay_counted(self):
        t = tmpdir(self)
        now = [1_000_000.0]
        led = Ledger(t / 's.db', {'claude': {'tokens_per_day': 1000, 'max_concurrent': 1}, 'stale_after_s': 60}, clock=lambda: now[0])
        r1, _ = led.reserve('a', 'p', 'claude', 600)      # worker crashes, never settles
        self.assertIsNone(led.reserve('a', 'p', 'claude', 10)[0])   # concurrency 1
        now[0] += 120                                       # stale: concurrency slot free, tokens still counted
        self.assertIsNone(led.reserve('a', 'p', 'claude', 500)[0])
        self.assertIsNotNone(led.reserve('a', 'p', 'claude', 300)[0])
        led2 = Ledger(t / 's.db', {'claude': {'tokens_per_day': 1000, 'max_concurrent': 5}, 'stale_after_s': 60}, clock=lambda: now[0])
        self.assertIsNone(led2.reserve('a', 'p', 'claude', 200)[0])   # survives a restart (same DB)
        now[0] += 86400 + 10                                           # rolling 24 h window
        self.assertIsNotNone(led2.reserve('a', 'p', 'claude', 900)[0])

    def test_release_only_for_never_sent(self):
        t = tmpdir(self)
        led = Ledger(t / 's.db', {'claude': {'calls_per_day': 1}})
        rid, _ = led.reserve('a', 'p', 'claude', 10)
        led.release(rid)
        self.assertIsNotNone(led.reserve('a', 'p', 'claude', 10)[0])

    def test_plan_guard(self):
        t = tmpdir(self)
        led = Ledger(t / 's.db', plan_probe=lambda: {'ok': True, 'five': {'p': 75.0}, 'week': {'p': 20.0}})
        rid, why = led.reserve('a', 'p', 'claude', 10)
        self.assertIsNone(rid)
        self.assertIn('5h', why)
        self.assertIsNotNone(led.reserve('a', 'p', 'helper:gemini', 10)[0])   # helpers are not on the Claude plan
        led2 = Ledger(t / 's2.db', {'plan_guard': {'fail_closed': True}}, plan_probe=lambda: None)
        self.assertIsNone(led2.reserve('a', 'p', 'claude', 10)[0])
        led3 = Ledger(t / 's3.db', plan_probe=lambda: (_ for _ in ()).throw(OSError('bridge down')))
        self.assertIsNotNone(led3.reserve('a', 'p', 'claude', 10)[0])            # unknown + not fail_closed -> allowed

    def test_units_are_reported_separately(self):
        t = tmpdir(self)
        led = Ledger(t / 's.db')
        rid, _ = led.reserve('a', 'p', 'claude:sonnet', 100)
        led.settle(rid, 80, 0.12)
        u = led.usage('a')
        self.assertEqual(u['claude']['tokens_24h'], 80)
        self.assertEqual(u['claude']['list_usd_24h_not_billed'], 0.12)
        self.assertIn('not an invoice', u['note'])


if __name__ == '__main__':
    unittest.main()
