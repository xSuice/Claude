"""Watchdog L3 (Recovery-Stufe 3): defekten Dienst mit Leitplanken neu starten.

Reine Unit-Tests mit injiziertem runner - kein echter systemd-Aufruf.
Leitplanken: Erst nach anhaltendem Ausfall, max. N Neustarts je Zeitfenster,
Meldung wenn Budget erschoepft, Zaehler-Reset bei Erholung.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, '/opt/jarvis/watchdog')
import watchdog  # noqa: E402


def fake_run(script):
    """script: list of (expected_argv_prefix, returncode). Consumed in order."""
    calls = []

    def run(argv, **kw):
        calls.append(list(argv))
        for prefix, rc in script:
            if list(argv[:len(prefix)]) == list(prefix):
                script.remove((prefix, rc))
                return _Completed(rc)
        return _Completed(0)
    return run, calls


class _Completed:
    def __init__(self, rc):
        self.returncode = rc


class L3ServiceRestart(unittest.TestCase):
    def scan(self, state, rc_active, now, down_for_s=60, max_restarts=3, window_s=3600):
        if not hasattr(self, '_all_calls'):
            self._all_calls = []
        events = []
        run, calls = fake_run([(['systemctl', 'is-active'], rc_active)])
        watchdog.services_scan(state, run=run, now=now, push_event=events.append,
                               down_for_s=down_for_s, max_restarts=max_restarts, window_s=window_s)
        self._all_calls.extend(calls)
        self.calls = self._all_calls
        return events

    def test_down_service_is_restarted_after_grace(self):
        state = {}
        events = self.scan(state, rc_active=3, now=1000)
        self.assertEqual(events, [])                       # Grace-Zeit noch nicht erreicht
        events = self.scan(state, rc_active=3, now=1000 + 120)
        self.assertEqual([e['event'] for e in events], ['restarted'])
        restart_call = [c for c in self.calls if 'restart' in c]
        self.assertEqual(len(restart_call), 1)
        self.assertEqual(restart_call[0][:2], ['sudo', '-n'])

    def test_healthy_service_resets_state(self):
        state = {'ma-claude-bridge': {'down_since': 500, 'restarts': [(400, 'cmd')]}}
        events = self.scan(state, rc_active=0, now=1000)
        self.assertEqual([e['event'] for e in events], ['service_recovered'])
        self.assertIsNone(state['ma-claude-bridge']['down_since'])

    def test_restart_budget_is_limited_and_reported(self):
        state = {}
        now = 1000
        seen = []
        for i in range(5):
            seen += self.scan(state, rc_active=3, now=now)
            now += 200                                   # bleibt down, grace laeuft weiter
        restarts = [c for c in self.calls if 'restart' in c]
        self.assertEqual(len(restarts), 3)               # Budget
        self.assertEqual([e['event'] for e in seen].count('restarted'), 3)
        self.assertIn('restart_budget_exhausted', [e['event'] for e in seen])
        self.assertNotIn('restart_budget_exhausted',
                         [e['event'] for e in self.scan(state, rc_active=3, now=now)])  # nur einmal

    def test_recovery_after_budget_clamps_and_allows_again(self):
        state = {}
        now = 1000
        for _ in range(4):
            self.scan(state, rc_active=3, now=now)
            now += 200
        self.scan(state, rc_active=0, now=now)           # Dienst kommt hoch
        self.scan(state, rc_active=0, now=now + 1)
        events = self.scan(state, rc_active=3, now=now + 2)
        self.assertNotIn('restart_budget_exhausted', [e['event'] for e in events])


if __name__ == '__main__':
    unittest.main()
