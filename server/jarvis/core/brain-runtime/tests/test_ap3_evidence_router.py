"""AP3 Acceptance Tests for evidence_router.py

Spec: KIMI_PRO_DIRECTOR_V2_PHASE_1_SPEC.md §3
AC1: EvidenceRouter class exists with choose() method
AC2: choose() uses Ledger.get_provider_quota() for quota checks
AC3: Strategic tasks prefer kimi_pro, routine prefer nexum
AC4: Fallback logic when primary provider quota exhausted
AC5: Decision logging to council_decisions
"""
import unittest
import tempfile
import json
from pathlib import Path
import sys

WORKTREE_RT = Path(r'C:/Users/andre/Documents/Hermes-Engineering-2026-10-17/jarvis-m1a-router-phase1/server/jarvis/core/brain-runtime')
sys.path.insert(0, str(WORKTREE_RT))

import ledger
from evidence_router import EvidenceRouter

class MockDB:
    """Mock database cursor for council_decisions logging."""
    def __init__(self):
        self.decisions = []

    def execute(self, sql, params):
        if 'council_decisions' in sql and 'INSERT' in sql:
            self.decisions.append(params)

class TestEvidenceRouter(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='test-ap3-')
        self.db = Path(self.tmpdir) / 'test.db'
        self.ledger = ledger.Ledger(self.db)
        self.mock_db = MockDB()
        self.router = EvidenceRouter(self.ledger, db_cursor=self.mock_db)

    def test_ac1_class_exists(self):
        """AC1: EvidenceRouter class exists"""
        self.assertIsInstance(self.router, EvidenceRouter)

    def test_ac1_choose_method_exists(self):
        """AC1: choose() method exists"""
        self.assertTrue(hasattr(self.router, 'choose'))
        self.assertTrue(callable(getattr(self.router, 'choose')))

    def test_ac2_choose_uses_quota(self):
        """AC2: choose() checks quota before selecting provider"""
        # Fresh ledger: both providers have quota
        result = self.router.choose('test task', complexity='routine')
        self.assertIn(result, ['nexum', 'local', None])  # routine -> nexum or local

    def test_ac3_strategic_prefers_kimi_pro(self):
        """AC3: Strategic tasks prefer kimi_pro"""
        result = self.router.choose('architecture decision', complexity='strategic', strategic_flag=True)
        self.assertEqual(result, 'kimi_pro')

    def test_ac3_routine_prefers_nexum(self):
        """AC3: Routine tasks prefer nexum"""
        result = self.router.choose('fix typo', complexity='routine')
        self.assertEqual(result, 'nexum')

    def test_ac4_fallback_on_quota_exhaustion(self):
        """AC4: Falls back when primary provider quota exhausted"""
        # Exhaust nexum calls (limit=500). settle() is required: quota
        # remaining_pct counts settled usage, and settling frees the
        # max_concurrent=5 slots so all 500 reservations succeed.
        for i in range(500):
            rid, _why = self.ledger.reserve('a', 'p', 'nexum', 100)
            assert rid is not None, f'reservation {i} should succeed'
            self.ledger.settle(rid, 100)

        # Now routine should fallback to local (spec AC4)
        result = self.router.choose('fix typo', complexity='routine')
        self.assertEqual(result, 'local')

    def test_ac4_critical_fail_closed(self):
        """AC4: Critical tasks fail closed if kimi_pro exhausted"""
        # Exhaust kimi_pro calls (limit=100); settle so usage counts
        for i in range(100):
            rid, _why = self.ledger.reserve('a', 'p', 'kimi_pro', 100)
            assert rid is not None, f'reservation {i} should succeed'
            self.ledger.settle(rid, 100)

        # Critical should return None (fail closed, spec AC2)
        result = self.router.choose('production outage', complexity='critical')
        self.assertIsNone(result)

    def test_ac5_decision_logging(self):
        """AC5: Decisions are logged to council_decisions"""
        result = self.router.choose('test task', complexity='routine')

        # Check that decision was logged
        self.assertGreater(len(self.mock_db.decisions), 0)

        # Parse logged outcome
        outcome_json = self.mock_db.decisions[0][0]
        outcome = json.loads(outcome_json)

        self.assertIn('provider', outcome)
        self.assertIn('complexity', outcome)
        self.assertIn('timestamp', outcome)

    def test_ac5_log_routing_decision_public_api(self):
        """AC5: spec-shaped log_routing_decision() writes council_decisions row"""
        db = MockDB()
        self.router.log_routing_decision(
            task_id='t-1', chosen_provider='nexum',
            complexity='routine', reason='routed to nexum', db_cursor=db)
        self.assertEqual(len(db.decisions), 1)
        outcome = json.loads(db.decisions[0][0])
        for key in ('provider', 'complexity', 'reason', 'kimi_remaining_pct',
                    'nexum_remaining_pct', 'tokens', 'cost_cents', 'model'):
            self.assertIn(key, outcome)

    def test_choose_returns_string_or_none(self):
        """choose() returns provider name or None"""
        result = self.router.choose('test', complexity='routine')
        self.assertIn(result, ['kimi_pro', 'nexum', 'local', None])

if __name__ == '__main__':
    unittest.main()
