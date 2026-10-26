#!/usr/bin/env python3
"""Fixture validity check: does the choice of observations matter at all? (v5.2.5, no LLM needed)

Input JSONL rows: case_id, family_id, stratum (S4|S5), d_budgeted_success, d_unbounded_success (booleans).
  d_budgeted   = D under the case's read_budget (the budget H gets as well)
  d_unbounded  = D allowed to read every catalog option (an upper bound for what any selection can reach)
selection_sensitive = d_unbounded succeeds AND d_budgeted fails. Only these cases leave room for H.
If the share is below the pre-registered minimum the fixture cannot show an H benefit: the correct
verdict is INCONCLUSIVE ("FIXTURE_SELECTION_INSENSITIVE"), never NO_GO about the model.
Run on DEV in M1a (D only) and by the evaluator on the holdout templates (D only, before B ever sees them).
"""
import argparse
import json
from pathlib import Path

MIN_SHARE = 0.30
STRATA = ('S4', 'S5')


def evaluate(path, min_share=MIN_SHARE):
    if min_share < MIN_SHARE:
        raise ValueError('Pre-registered minimum share may not be lowered')
    counts = {s: [0, 0] for s in STRATA}  # sensitive, total
    seen = set()
    for n, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get('stratum') not in counts:
            raise ValueError(f'Zeile {n}: nur S4/S5 erlaubt')
        if not isinstance(r.get('case_id'), str) or r['case_id'] in seen:
            raise ValueError(f'Zeile {n}: fehlende/doppelte case_id')
        if not all(type(r.get(k)) is bool for k in ('d_budgeted_success', 'd_unbounded_success')):
            raise ValueError(f'Zeile {n}: Outcomes müssen Booleans sein')
        if r['d_budgeted_success'] and not r['d_unbounded_success']:
            raise ValueError(f'Zeile {n}: budgetiertes D erfolgreich, unbegrenztes nicht (Harness-Fehler)')
        seen.add(r['case_id'])
        c = counts[r['stratum']]
        c[1] += 1
        c[0] += int(r['d_unbounded_success'] and not r['d_budgeted_success'])
    out = {}
    valid = True
    for s, (sens, tot) in counts.items():
        share = sens / tot if tot else 0.0
        out[s] = {'selection_sensitive': sens, 'total': tot, 'share': round(share, 4)}
        valid = valid and tot > 0 and share >= min_share
    return {'per_stratum': out, 'min_share': min_share,
            'status': 'FIXTURE_VALID' if valid else 'FIXTURE_SELECTION_INSENSITIVE'}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--jsonl', required=True)
    print(json.dumps(evaluate(ap.parse_args().jsonl), indent=2))
