"""Deterministic Strategic/Routine/Critical Task Classifier for Kimi-V2 Phase 1.

Keyword-based classification — NO LLM calls (§12). Runs before router.choose()
to set task complexity tier for model-tier routing (Kimi=strategic, Nexum=routine).

Part of KIMI_PRO_DIRECTOR_V2 Phase 1, Arbeitspaket 2.
"""
from __future__ import annotations

from typing import Literal

ComplexityTier = Literal['routine', 'strategic', 'critical']

STRATEGIC_KEYWORDS = [
    'architektur', 'design', 'plan', 'strategie', 'entscheidung',
    'integration', 'migration', 'refactor', 'security', 'governance',
    'council', 'phase', 'spec', 'roadmap', 'analyse', 'gutachten',
    'konzept', 'evaluierung', 'auswahl', 'budget', 'kosten', 'prognose',
    'priorisierung', 'schnittstelle', 'datenschutz', 'compliance',
]

ROUTINE_KEYWORDS = [
    'bug', 'fix', 'test', 'lint', 'format', 'update', 'bump',
    'dependency', 'readme', 'docs', 'typo', 'log', 'cleanup',
    'patch', 'hotfix', 'deploy', 'release', 'check', 'verify',
    'monitor', 'alert', 'config', 'backup', 'restore', 'cron',
    'status', 'health', 'ping', 'heartbeat', 'restart',
]

CRITICAL_KEYWORDS = [
    'outage', 'down', 'broken', 'emergency', 'rollback',
    'security breach', 'data loss', 'production', 'p0', 'p1',
    'notfall', 'kritisch', 'urgent', 'dringend', 'ausfall', 'downtime',
    'crash', 'absturz', 'datenverlust', 'korruption', 'sicherheitsvorfall',
    'breach', 'leak', 'compromised', 'wiederherstellung', 'sofort',
    'blocker', 'blocking', 'deadlock', 'stuck',
]


class TaskClassifier:
    """Deterministic keyword-based task classifier."""

    def classify(self, task_payload: str) -> dict:
        """
        Classify a task based on text content.

        Args:
            task_payload: Task title + description + any context

        Returns:
            {
                'complexity': 'routine' | 'strategic' | 'critical',
                'strategic_flag': bool,
                'confidence': float,  # 0.0-1.0, based on keyword hit count
                'matched_keywords': list[str]
            }
        """
        text = task_payload.lower()

        # Count hits per tier
        critical_hits = [kw for kw in CRITICAL_KEYWORDS if kw in text]
        strategic_hits = [kw for kw in STRATEGIC_KEYWORDS if kw in text]
        routine_hits = [kw for kw in ROUTINE_KEYWORDS if kw in text]

        # Priority: critical > strategic > routine
        if critical_hits:
            return {
                'complexity': 'critical',
                'strategic_flag': True,
                'confidence': min(1.0, 0.5 + 0.2 * len(critical_hits)),
                'matched_keywords': critical_hits
            }
        elif strategic_hits and len(strategic_hits) >= len(routine_hits):
            return {
                'complexity': 'strategic',
                'strategic_flag': True,
                'confidence': min(1.0, 0.4 + 0.15 * len(strategic_hits)),
                'matched_keywords': strategic_hits
            }
        else:
            return {
                'complexity': 'routine',
                'strategic_flag': False,
                'confidence': min(1.0, 0.4 + 0.1 * len(routine_hits)) if routine_hits else 0.3,
                'matched_keywords': routine_hits
            }

    def classify_and_tag(self, task_id: str, task_payload: str, db_cursor) -> dict:
        """
        Classify and UPDATE tasks table with complexity + strategic_flag.

        Args:
            task_id: tasks.task_id
            task_payload: Text to classify
            db_cursor: sqlite3 or psycopg2 cursor (auto-detects placeholder style)

        Returns:
            classification dict (see classify())
        """
        result = self.classify(task_payload)
        # Support both sqlite3 (?) and psycopg2 (%s) cursors
        try:
            db_cursor.execute(
                "UPDATE tasks SET complexity = ?, strategic_flag = ? WHERE task_id = ?",
                (result['complexity'], result['strategic_flag'], task_id)
            )
        except Exception:
            db_cursor.execute(
                "UPDATE tasks SET complexity = %s, strategic_flag = %s WHERE task_id = %s",
                (result['complexity'], result['strategic_flag'], task_id)
            )
        return result


# Backward-compatible convenience function for existing call sites
def classify(title: str, description: str = '') -> ComplexityTier:
    """Standalone function wrapper for backward compatibility."""
    return TaskClassifier().classify(f'{title} {description}')['complexity']


if __name__ == '__main__':
    # AC1-AC3 self-test
    c = TaskClassifier()
    tests = [
        ('Architektur-Entscheidung für Council-System', 'strategic', True),
        ('Fix typo in README', 'routine', False),
        ('PRODUCTION OUTAGE: data loss in tasks table', 'critical', True),
        ('Server crashed, data loss risk', 'critical', True),
        ('Budget-Prognose Q4 Kostenoptimierung', 'strategic', True),
        ('Deploy hotfix to staging', 'routine', False),
        ('Unbekannter Task ohne Keywords', 'routine', False),
    ]
    passed = 0
    for payload, exp_complexity, exp_flag in tests:
        result = c.classify(payload)
        ok = result['complexity'] == exp_complexity and result['strategic_flag'] == exp_flag
        status = 'PASS' if ok else 'FAIL'
        if ok:
            passed += 1
        print(f"[{status}] classify('{payload[:50]}...') = {result['complexity']}, "
              f"flag={result['strategic_flag']}, conf={result['confidence']:.2f}, "
              f"kw={result['matched_keywords'][:3]}")
    print(f'\n{passed}/{len(tests)} tests passed')
