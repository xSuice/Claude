#!/usr/bin/env python3
"""V11.1 explicit canary runs: the ONLY way a cloud helper earns trust before production use.

Shadow mode never calls a helper (audit P0-1), so trust data must come from somewhere safe:
a suite of PUBLIC test cases with deterministic verifiers, run on demand by the operator.

Gates (all fail closed):
  providers.json canary.enabled == true (default false) -> every normal helper gate (cloud_enabled,
  provider enabled, task type, egress rule for class "public", rate limits, call/token budgets,
  breaker) -> each case must classify as public (secrets / personal data are refused, never sent)
  -> at most canary.max_calls_per_run requests per run (default 3, max 20).
Every answer is judged by helper_verify (suspicious = failure) and recorded with origin='canary';
those verdicts are what route_policy uses for min_samples / min_success.

Suite file (JSON): {"cases": [{"id": "c1", "task_type": "diagnose_hint", "prompt": "...",
                               "verify": {"type": "grounded" | "contains" | "json_keys", ...}}]}
Usage: python3 canary.py --providers providers.json --db helpers.sqlite3 --identity person-a \
       --project ma-home --provider groq --suite canary-suite.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from helper_verify import PROMPTS, verify
from provider_adapter import HelperClient, Refused, classify, load


def run(helpers: HelperClient, suite: Path, *, provider: str, project: str) -> dict:
    can = helpers.cfg.get('canary', {})
    if not can.get('enabled'):
        raise PermissionError('canary runs are disabled (providers.json canary.enabled=false)')
    cap = can.get('max_calls_per_run', 3)
    cases = json.loads(Path(suite).read_text(encoding='utf-8'))['cases']
    out = {'provider': provider, 'results': [], 'refused': [], 'cap': cap}
    for case in cases:
        if len(out['results']) >= cap:
            out['refused'].append({'id': case.get('id'), 'why': 'run cap reached'}); continue
        prompt, vspec = str(case.get('prompt', '')), case.get('verify') or {'type': 'grounded'}
        if classify(prompt, 'public') != 'public':
            out['refused'].append({'id': case.get('id'), 'why': 'not public data - never sent'}); continue
        try:
            r = helpers.call(provider, case['task_type'], PROMPTS.get(vspec.get('type'), '') + prompt, project=project,
                             declared_class='public', order_id=f"canary:{case.get('id')}", origin='canary')
        except Refused as e:
            out['refused'].append({'id': case.get('id'), 'why': str(e)})
            if 'budget' in str(e) or 'limit' in str(e) or 'circuit' in str(e):
                break                                       # no point hammering a closed gate
            continue
        ok, why = verify(vspec, r['text'], prompt, r['suspicious'])
        helpers.mark_call(r['call_id'], ok, why)
        out['results'].append({'id': case.get('id'), 'verified': ok, 'why': why, 'latency_ms': r['latency_ms'],
                               'tokens': r['usage'], 'cost_usd': r['cost_usd']})
    n = len(out['results'])
    out['verified_rate'] = round(sum(x['verified'] for x in out['results']) / n, 3) if n else None
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    for k in ('providers', 'db', 'identity', 'project', 'provider', 'suite'):
        ap.add_argument(f'--{k}', required=True)
    a = ap.parse_args()
    h = HelperClient(load(Path(a.providers)), Path(a.db), a.identity)
    try:
        print(json.dumps(run(h, Path(a.suite), provider=a.provider, project=a.project), ensure_ascii=False, indent=1))
    except PermissionError as e:
        print(f'ERROR: {e}', file=sys.stderr); return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
