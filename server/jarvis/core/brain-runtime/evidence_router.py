"""Evidence-based router for Kimi-V2 multi-provider orchestration.

Routes tasks to Kimi Pro (strategic), Nexum (routine), or local fallback
based on: complexity, provider quota, cost budget, and fail_closed policy.

Fails CLOSED: if no provider is safe, refuse to route (no silent fallback
to expensive models).

Spec: KIMI_PRO_DIRECTOR_V2_PHASE_1_SPEC.md §3
"""
from __future__ import annotations

import json
import time
from typing import Optional

import ledger

class EvidenceRouter:
    """Routes tasks based on evidence: complexity + quota + cost.

    Decision logic:
    - critical → kimi_pro (if quota OK), else None (fail closed)
    - strategic → kimi_pro (if quota OK), else nexum (if quota OK), else None
    - routine → nexum (if quota OK), else local, else None

    All decisions are logged to council_decisions for audit trail.
    """

    def __init__(self, ledger_instance: ledger.Ledger, db_cursor=None, fail_closed: bool = True):
        """Initialize router with a Ledger instance for quota checks.

        Args:
            ledger_instance: Ledger instance for quota queries
            db_cursor: Optional database cursor for decision logging
            fail_closed: If True, return None when no safe option (default True)
        """
        self.ledger = ledger_instance
        self.db_cursor = db_cursor
        self.fail_closed = fail_closed

    def choose(
        self,
        task_text: str,
        complexity: str = 'routine',
        strategic_flag: bool = False
    ) -> Optional[str]:
        """Choose a provider for a task.

        Args:
            task_text: Task payload (for future LLM-based routing, unused now)
            complexity: 'routine', 'strategic', or 'critical'
            strategic_flag: Whether task is flagged as strategic

        Returns:
            'kimi_pro', 'nexum', 'local', or None (if fail_closed and no safe option)
        """
        try:
            kimi_quota = self.ledger.get_provider_quota('kimi_pro')
            nexum_quota = self.ledger.get_provider_quota('nexum')
        except KeyError:
            # Provider not configured - fail closed
            self._log_decision(None, complexity, strategic_flag, 'provider_not_configured')
            return None

        kimi_ok = kimi_quota['remaining_pct'] > 10.0  # >10% remaining
        nexum_ok = nexum_quota['remaining_pct'] > 10.0

        provider = None
        reason = ''

        if complexity == 'critical':
            provider = 'kimi_pro' if kimi_ok else None
            reason = 'critical_task' if kimi_ok else 'critical_kimi_exhausted'

        elif complexity == 'strategic' or strategic_flag:
            if kimi_ok:
                provider = 'kimi_pro'
                reason = 'strategic_kimi_available'
            elif nexum_ok:
                provider = 'nexum'
                reason = 'strategic_fallback_nexum'
            else:
                reason = 'strategic_all_exhausted'

        else:  # routine
            if nexum_ok:
                provider = 'nexum'
                reason = 'routine_nexum_available'
            else:
                provider = 'local'
                reason = 'routine_fallback_local'

        # Log decision
        self._log_decision(provider, complexity, strategic_flag, reason)

        return provider

    def log_routing_decision(
        self,
        task_id: str,
        chosen_provider: Optional[str],
        complexity: str,
        reason: str,
        db_cursor,
    ) -> None:
        """Spec §3.1 public audit entry: write one council_decisions row.

        outcome JSONB schema per spec: provider, complexity, reason,
        kimi_remaining_pct, nexum_remaining_pct, tokens, cost_cents, model.
        """
        try:
            kimi_pct = self.ledger.get_provider_quota('kimi_pro')['remaining_pct']
            nexum_pct = self.ledger.get_provider_quota('nexum')['remaining_pct']
        except KeyError:
            kimi_pct = nexum_pct = 0.0

        outcome = {
            'provider': chosen_provider,
            'complexity': complexity,
            'reason': reason,
            'kimi_remaining_pct': kimi_pct,
            'nexum_remaining_pct': nexum_pct,
            'tokens': 0,        # estimate, 0 at routing time
            'cost_cents': 0,    # estimate, 0 at routing time
            'model': chosen_provider or 'none',
            'task_id': task_id,
        }

        try:
            db_cursor.execute(
                """INSERT INTO council_decisions
                   (decision_id, council_name, decision_type, outcome)
                   VALUES (gen_random_uuid()::text, 'evidence_router', 'routing_decision', %s::jsonb)""",
                (json.dumps(outcome),)
            )
        except Exception:  # noqa: BLE001 - logging failure must not block routing
            pass

    def _log_decision(
        self,
        provider: Optional[str],
        complexity: str,
        strategic_flag: bool,
        reason: str
    ) -> None:
        """Log routing decision to council_decisions for audit trail.

        Args:
            provider: Selected provider or None
            complexity: Task complexity
            strategic_flag: Strategic flag
            reason: Decision reason
        """
        if not self.db_cursor:
            return

        outcome = {
            'provider': provider,
            'complexity': complexity,
            'strategic_flag': strategic_flag,
            'reason': reason,
            'timestamp': int(time.time()),
            'fail_closed': self.fail_closed,
        }

        try:
            self.db_cursor.execute(
                """INSERT INTO council_decisions
                   (decision_id, council_name, decision_type, outcome)
                   VALUES (gen_random_uuid()::text, 'evidence_router', 'routing_decision', %s::jsonb)""",
                (json.dumps(outcome),)
            )
        except Exception:  # noqa: BLE001 - logging failure must not block routing
            pass
