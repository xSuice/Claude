#!/usr/bin/env python3
"""V11 adapter between the brain's orders and the EXISTING MA Auto Router - not a router.

Contract (documented in ROUTER-INTERFACE.md): the router is asked through a configured
command (`router_cmd`, argv list, no shell). It reads one JSON request on stdin
  {"task_type", "risk", "data_class", "size_chars", "has_procedure"}
and prints one JSON decision {"target": "local" | "helper:<name>" | "claude[:<model>]" | "human",
"reason": "..."}. If no router command is configured or it fails, the adapter reproduces
the brain's existing behaviour (status quo) - it never invents a second policy.

Mode 'shadow' (default): the status-quo decision is executed - a helper is NEVER called, even when
the router names one (V11.1); the router's choice and the eligible candidate are only recorded. The adapter additionally
records which helper COULD have been used (eligible, measured reliability) so routes can be
compared on real data before anything is switched. Mode 'active' only uses a helper when the
router itself names it, cloud is enabled, the provider is eligible for this data class and its
measured verified success is >= min_success over >= min_samples.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import time
from pathlib import Path

TARGETS = ('local', 'helper', 'claude', 'human')
SHADOW = '''CREATE TABLE IF NOT EXISTS route_shadow(id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL,
    order_id TEXT, task_type TEXT, data_class TEXT, router TEXT NOT NULL, executed TEXT NOT NULL, candidate TEXT,
    candidate_reason TEXT, outcome TEXT)'''


def status_quo(req: dict) -> dict:
    """What V10.1 already does: known procedure -> local; otherwise Claude via the queue for
    severe diagnosis, human for the rest. Used only when the real router is unavailable."""
    if req.get('has_procedure'):
        return {'target': 'local', 'reason': 'confirmed procedure'}
    if (req.get('task_type') == 'diagnosis' or req.get('fallback') == 'claude') and req.get('risk') in ('read', 'reversible'):
        return {'target': 'claude', 'reason': 'status quo: Claude via the bounded queue'}
    return {'target': 'human', 'reason': 'status quo: no automatic route'}


class RoutePolicy:
    def __init__(self, db: Path, router_cmd: list[str] | None = None, helpers=None, mode='shadow',
                 min_success=0.8, min_samples=10, provider_order=()):
        if mode not in ('shadow', 'active'):
            raise ValueError('mode must be shadow or active')
        self.db, self.cmd, self.helpers, self.mode = Path(db), router_cmd, helpers, mode
        self.min_success, self.min_samples, self.order = min_success, min_samples, list(provider_order)
        c = sqlite3.connect(str(self.db))
        try:
            c.execute(SHADOW); c.commit()
        finally:
            c.close()

    def ask_router(self, req: dict) -> dict:
        if not self.cmd:
            return {**status_quo(req), 'source': 'status_quo (no router_cmd configured)'}
        try:
            p = subprocess.run(self.cmd, input=json.dumps(req), capture_output=True, text=True, timeout=10)
            d = json.loads(p.stdout)
            tgt = str(d.get('target', ''))
            if p.returncode != 0 or tgt.split(':')[0] not in TARGETS:
                raise ValueError('bad router answer')
            return {'target': tgt, 'reason': str(d.get('reason', ''))[:200], 'source': 'ma-auto-router'}
        except (OSError, ValueError, subprocess.TimeoutExpired):
            return {**status_quo(req), 'source': 'status_quo (router unavailable)'}

    def _reliable(self, provider, task_type):
        if not self.helpers:
            return False, 'no helper client'
        for s in self.helpers.stats():
            if s['provider'] == provider and s['task_type'] == task_type:
                n = (s['verified_ok'] or 0) + (s['verified_bad'] or 0)
                if n < self.min_samples:
                    return False, f'only {n} verified samples'
                rate = (s['verified_ok'] or 0) / n
                return rate >= self.min_success, f'verified success {rate:.2f} over {n}'
        return False, 'no measurements yet'

    def candidate(self, req: dict, project: str) -> tuple[str | None, str]:
        if not self.helpers:
            return None, 'helpers not configured'
        for prov in self.order:
            why = self.helpers.eligible(prov, req['task_type'], req['data_class'], project)
            if why is None:
                ok, rel = self._reliable(prov, req['task_type'])
                return f'helper:{prov}', rel + ('' if ok else ' (not yet trusted)')
        return None, 'no eligible helper'

    def decide(self, req: dict, project: str, order_id: str | None = None) -> dict:
        router = self.ask_router(req)
        cand, why = self.candidate(req, project)
        executed = router['target']
        if self.mode == 'shadow' and router['target'].startswith('helper:'):
            # V11.1 (audit P0-1): shadow never calls a helper - the router's choice is recorded, the
            # V10.1 status-quo path is executed. Trust is built only by explicit canary runs (canary.py).
            executed = status_quo(req)['target']
            why = f"shadow: router chose {router['target']} (not executed); " + why
        elif self.mode == 'active' and router['target'].startswith('helper:'):
            prov = router['target'].split(':', 1)[1]
            ok, rel = self._reliable(prov, req['task_type'])
            if not self.helpers or self.helpers.eligible(prov, req['task_type'], req['data_class'], project) or not ok:
                executed = status_quo(req)['target']  # the router's helper choice is not (yet) allowed/trusted
                why = f'router chose {prov}, refused: ' + (rel if not ok else 'not eligible')
        c = sqlite3.connect(str(self.db))
        try:
            c.execute('INSERT INTO route_shadow(ts,order_id,task_type,data_class,router,executed,candidate,candidate_reason) '
                      'VALUES(?,?,?,?,?,?,?,?)', (int(time.time()), order_id, req.get('task_type'), req.get('data_class'),
                                                  json.dumps(router), executed, cand, why))
            c.commit()
        finally:
            c.close()
        return {'router': router, 'executed': executed, 'shadow_candidate': cand, 'candidate_reason': why,
                'mode': self.mode}

    def compare(self, days=30) -> list[dict]:
        since = int(time.time()) - days * 86400
        c = sqlite3.connect(str(self.db))
        try:
            rows = c.execute('SELECT task_type, executed, candidate, COUNT(*) FROM route_shadow WHERE ts>=? '
                             'GROUP BY task_type, executed, candidate', (since,)).fetchall()
        finally:
            c.close()
        return [{'task_type': r[0], 'executed': r[1], 'candidate': r[2], 'n': r[3]} for r in rows]
