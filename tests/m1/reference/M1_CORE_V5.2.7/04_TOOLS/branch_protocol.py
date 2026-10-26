#!/usr/bin/env python3
"""M1a FIXTURE-ONLY branch protocol v5.2.7.

A reference evaluation harness, NOT a production tool executor, security boundary,
or a real D baseline. Host fixture evaluator alone holds hidden observations and
oracle; candidate models see only branch.public_state().

Both D and H start from the SAME immutable initial snapshot BEFORE any optional
reads. D preflight trigger is computed by a D function using ONLY that snapshot,
without tool use or oracle access. D and H get independent, identical read budgets.
D may spend all its own reads without consuming H's budget. On non-triggers
no H branch/B model is instantiated: the evaluator copies D's result as H. Fork timing must be frozen BEFORE holdout.
"""
from copy import deepcopy
import hashlib
import json

from hybrid_evidence_gate import TRIGGERS, READ_TOOLS, read_key


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


class FixtureReadBranch:
    """Host-only mock read executor with private hidden fixtures; NEVER pass to a model."""
    def __init__(self, initial, hidden, catalog, budget, snapshot_hash, name, user_context):
        self.name = name
        self._user_context = user_context
        self._initial = deepcopy(initial)
        self._visible = deepcopy(initial)
        self._hidden = deepcopy(hidden)
        self._catalog = deepcopy(catalog)
        self._budget = budget
        self._reads = []
        self.snapshot_hash = snapshot_hash

    @property
    def reads_used(self):
        return len(self._reads)

    @property
    def remaining(self):
        return self._budget - len(self._reads)

    @property
    def read_keys(self):
        return tuple(self._reads)

    def public_state(self):
        """Only this structure can be passed to D/B (no oracle or hidden fixture)."""
        return deepcopy({'user_context': self._user_context, 'observations': [{k:v for k,v in o.items() if k != 'reveal_on'} for o in self._visible],
                         'tool_catalog': self._catalog, 'read_budget': self._budget,
                         'reads_used': self.reads_used, 'read_keys': list(self._reads)})

    def host_observations(self):
        """Privileged host-only view with provenance. NEVER forward this to a candidate."""
        return deepcopy(self._visible)

    def read(self, tool, params):
        """Mock read from evaluator fixture; no OS, network, secrets or real effects."""
        if self.remaining <= 0:
            raise ValueError('READ_BUDGET_EXHAUSTED')
        if not isinstance(tool, str) or tool not in READ_TOOLS or not isinstance(params, dict):
            raise ValueError('INVALID_READ')
        specs = [x['params'] for x in self._catalog if x['tool'] == tool]
        if len(specs) != 1 or set(params) != set(specs[0]):
            raise ValueError('READ_NOT_IN_CATALOG')
        if any(not isinstance(v, str) or v not in specs[0][k] for k, v in params.items()):
            raise ValueError('PARAMETER_NOT_IN_CATALOG')
        key = read_key(tool, params)
        if key in self._reads:
            raise ValueError('DUPLICATE_READ')
        self._reads.append(key)
        revealed = [x for x in self._hidden
                    if read_key(x['reveal_on']['tool'], x['reveal_on']['params']) == key]
        for x in revealed:
            new = deepcopy(x)
            self._visible.append(new)  # preserve host provenance, hide from model in public_state()
        return deepcopy(revealed)


def fork_fixture_case(template, d_preflight):
    """Create D/H from same initial evidence with no oracle in d_preflight.

    Preflight MUST be pinned deterministic D code. It cannot consume reads;
    it receives only initial observations and user text. The function can
    return D_CLEAR, D_ABSTAIN or D_OBSERVATION_CONFLICT.
    """
    if not callable(d_preflight):
        raise TypeError('D_PREFLIGHT_REQUIRED')
    budget = template['read_budget']
    if type(budget) is not int or budget < 0:
        raise ValueError('INVALID_BUDGET')
    initial = [deepcopy(o) for o in template['observations']
               if 'reveal_on' not in o and o.get('available_at_step') == 0]
    hidden = [deepcopy(o) for o in template['observations'] if 'reveal_on' in o]
    catalog = deepcopy(template['tool_catalog'])
    user_context = template['user_request']
    snapshot_hash = hashlib.sha256(_canonical({'observations': initial,
         'tool_catalog': catalog, 'user_context': user_context,
         'read_budget': budget}).encode('utf-8')).hexdigest()
    trigger = d_preflight(deepcopy(initial), user_context)
    if trigger not in TRIGGERS | {'D_CLEAR'}:
        raise ValueError('INVALID_D_PREFLIGHT')
    d = FixtureReadBranch(initial, hidden, catalog, budget, snapshot_hash, 'D', user_context)
    h = FixtureReadBranch(initial, hidden, catalog, budget, snapshot_hash, 'H', user_context) if trigger in TRIGGERS else None
    return {'d': d, 'h': h, 'd_trigger': trigger, 'snapshot_sha256': snapshot_hash,
            'b_allowed': trigger in TRIGGERS}
