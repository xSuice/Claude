#!/usr/bin/env python3
"""Predeclared stratified paired CLUSTER percentile bootstrap for binary M1 outcomes (v5.2.5).

Input JSONL: one row per case_id, columns:
  case_id, family_id, stratum (S1..S6), d_success, b_success, h_success, h_triggered (booleans).
The evaluator must assert *semantic* case success using the oracle first.

Why clusters: cases from one template family are correlated. Resampling single cases would make the
CI too narrow. The resampling unit is therefore the family_id inside each stratum.
Few clusters still give optimistic CIs, so the tool also reports per-(stratum,family) cell effects;
the pre-registered gate additionally requires that most cells are not negative.

Groups (pre-registered):
  easy        = S1,S2,S3   non-inferiority
  improvement = S4,S5      improvement
  s6          = S6         no regression (H equals D by construction when B cannot verify a cause)
Run only once on the blind holdout, never to tune candidates.
"""
import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path

STRATA = ('S1', 'S2', 'S3', 'S4', 'S5', 'S6')
EASY = ('S1', 'S2', 'S3')
IMPROVE = ('S4', 'S5')
S6 = ('S6',)
MIN_PAIRS = {'S1': 30, 'S2': 30, 'S3': 30, 'S4': 60, 'S5': 60, 'S6': 30}
MIN_FAMILIES = 6
MAX_FAMILY_SHARE = 0.35
SEED = 20261016
ITERATIONS = 20000


def load_pairs(path, min_easy=30, min_improve=60, min_s6=30, min_families=MIN_FAMILIES,
               max_family_share=MAX_FAMILY_SHARE):
    """Floors are hard-coded: arguments can raise, never lower, the pre-registered minimums."""
    groups = {x: [] for x in STRATA}
    seen = set()
    for line_number, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        r = json.loads(line)
        if not isinstance(r, dict) or r.get('stratum') not in groups:
            raise ValueError(f'Zeile {line_number}: unbekanntes Stratum')
        if not isinstance(r.get('case_id'), str) or not r['case_id'] or r['case_id'] in seen:
            raise ValueError(f'Zeile {line_number}: fehlende/doppelte case_id')
        if not isinstance(r.get('family_id'), str) or not r['family_id']:
            raise ValueError(f'Zeile {line_number}: family_id fehlt')
        if not all(type(r.get(k)) is bool for k in ('d_success', 'b_success', 'h_success', 'h_triggered')):
            raise ValueError(f'Zeile {line_number}: Outcomes müssen echte Booleans sein')
        # Without a trigger only D runs: any difference is a harness/data integrity error.
        if not r['h_triggered'] and r['h_success'] != r['d_success']:
            raise ValueError(f'Zeile {line_number}: H ohne Trigger muss exakt D entsprechen')
        seen.add(r['case_id'])
        groups[r['stratum']].append(r)
    floors = {'S1': min_easy, 'S2': min_easy, 'S3': min_easy, 'S4': min_improve, 'S5': min_improve, 'S6': min_s6}
    for s, vals in groups.items():
        required = max(MIN_PAIRS[s], floors[s])
        if len(vals) < required:
            raise ValueError(f'{s}: {len(vals)} Paare statt mindestens {required}')
        fams = defaultdict(int)
        for v in vals:
            fams[v['family_id']] += 1
        if len(fams) < max(MIN_FAMILIES, min_families):
            raise ValueError(f'{s}: {len(fams)} Familien statt mindestens {max(MIN_FAMILIES, min_families)}')
        biggest = max(fams.values()) / len(vals)
        if biggest > min(MAX_FAMILY_SHARE, max_family_share) + 1e-12:
            raise ValueError(f'{s}: eine Familie stellt {biggest:.0%} der Fälle (max {MAX_FAMILY_SHARE:.0%})')
    return groups


def percentile(sorted_vals, probability):
    position = (len(sorted_vals) - 1) * probability
    low, high = math.floor(position), math.ceil(position)
    if low == high:
        return sorted_vals[low]
    return sorted_vals[low] * (high - position) + sorted_vals[high] * (position - low)


def _diff(r, candidate):
    return int(r[f'{candidate}_success']) - int(r['d_success'])


def _clusters(rows, candidate):
    """[(sum_of_diffs, n)] per family."""
    acc = defaultdict(lambda: [0, 0])
    for r in rows:
        a = acc[r['family_id']]
        a[0] += _diff(r, candidate)
        a[1] += 1
    return [tuple(v) for _, v in sorted(acc.items())]


def effect(groups, candidate, strata):
    means = []
    for s in strata:
        vals = groups[s]
        means.append(sum(_diff(v, candidate) for v in vals) / len(vals))
    return sum(means) / len(means) * 100


def bootstrap(groups, candidate, strata, *, iterations=ITERATIONS, seed=SEED):
    """Equal-weight mean over strata; families resampled with replacement inside each stratum."""
    rng = random.Random(seed)
    estimate = effect(groups, candidate, strata)
    cl = {s: _clusters(groups[s], candidate) for s in strata}
    vals = []
    for _ in range(iterations):
        means = []
        for s in strata:
            c = cl[s]
            k = len(c)
            tot = n = 0
            for _ in range(k):
                d, m = c[rng.randrange(k)]
                tot += d
                n += m
            means.append(tot / n)
        vals.append(sum(means) / len(means) * 100)
    vals.sort()
    return {'candidate': candidate, 'strata': list(strata), 'estimate_pp': round(estimate, 4),
            'ci_lower_pp': round(percentile(vals, 0.025), 4),
            'ci_upper_pp': round(percentile(vals, 0.975), 4),
            'seed': seed, 'iterations': iterations,
            'resample_unit': 'family_id_within_stratum', 'stratification': 'equal_weight_per_stratum'}


def naive_case_level(groups, candidate, strata, *, iterations=ITERATIONS, seed=SEED):
    """DIAGNOSTIC ONLY (too narrow if families are correlated). Never used for gates."""
    rng = random.Random(seed)
    diffs = {s: [_diff(r, candidate) for r in groups[s]] for s in strata}
    vals = []
    for _ in range(iterations):
        means = []
        for s in strata:
            d = diffs[s]
            n = len(d)
            means.append(sum(d[rng.randrange(n)] for _ in range(n)) / n)
        vals.append(sum(means) / len(means) * 100)
    vals.sort()
    return {'ci_lower_pp': round(percentile(vals, 0.025), 4), 'ci_upper_pp': round(percentile(vals, 0.975), 4),
            'note': 'diagnostic_only_not_a_gate'}


def family_cells(groups, candidate, strata):
    """Per (stratum,family) mean difference in pp plus counts. Raw inputs for the cell-consistency gate."""
    cells = []
    for s in strata:
        for fam, (d, n) in zip(sorted({r['family_id'] for r in groups[s]}), _clusters(groups[s], candidate)):
            cells.append({'stratum': s, 'family_id': fam, 'n': n, 'diff_pp': round(d / n * 100, 4)})
    pos = sum(c['diff_pp'] > 0 for c in cells)
    neg = sum(c['diff_pp'] < 0 for c in cells)
    total = len(cells)
    return {'cells': cells, 'positive_fraction': round(pos / total, 4),
            'negative_fraction': round(neg / total, 4), 'cell_count': total}


def triggered_bootstrap(groups, *, iterations=ITERATIONS, seed=SEED, minimum=30, min_families=4):
    """Planned LIMITED_GO subset: only D-triggered S4/S5 cases, family clusters pooled."""
    selected = [r for s in IMPROVE for r in groups[s] if r['h_triggered']]
    fams = {(r['stratum'], r['family_id']) for r in selected}
    if len(selected) < minimum or len(fams) < min_families:
        return {'status': 'INCONCLUSIVE', 'triggered_n': len(selected), 'triggered_families': len(fams),
                'required_n': minimum, 'required_families': min_families}
    acc = defaultdict(lambda: [0, 0])
    for r in selected:
        a = acc[(r['stratum'], r['family_id'])]
        a[0] += _diff(r, 'h')
        a[1] += 1
    c = [tuple(v) for _, v in sorted(acc.items())]
    rng = random.Random(seed)
    k = len(c)
    vals = []
    for _ in range(iterations):
        tot = n = 0
        for _ in range(k):
            d, m = c[rng.randrange(k)]
            tot += d
            n += m
        vals.append(tot / n * 100)
    vals.sort()
    return {'status': 'CALCULATED', 'triggered_n': len(selected), 'triggered_families': len(fams),
            'estimate_pp': round(sum(_diff(r, 'h') for r in selected) / len(selected) * 100, 4),
            'ci_lower_pp': round(percentile(vals, 0.025), 4), 'ci_upper_pp': round(percentile(vals, 0.975), 4),
            'seed': seed, 'iterations': iterations,
            'method': 'pooled_paired_family_cluster_percentile_bootstrap_triggered_S4_S5'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--jsonl', required=True)
    p.add_argument('--iterations', type=int, default=ITERATIONS)
    p.add_argument('--seed', type=int, default=SEED)
    a = p.parse_args()
    if a.seed != SEED or a.iterations != ITERATIONS:
        raise SystemExit(f'Pre-registered statistics must use exactly seed={SEED}, iterations={ITERATIONS}')
    groups = load_pairs(a.jsonl)
    comparisons = []
    for candidate in ('h', 'b'):
        for name, strata in (('easy', EASY), ('improvement', IMPROVE), ('s6', S6)):
            res = bootstrap(groups, candidate, strata)
            res['group'] = name
            res['naive_case_level_diagnostic'] = naive_case_level(groups, candidate, strata)
            comparisons.append(res)
    result = {'n_by_stratum': {s: len(x) for s, x in groups.items()},
              'families_by_stratum': {s: len({r['family_id'] for r in x}) for s, x in groups.items()},
              'comparisons': comparisons,
              'h_improvement_family_cells': family_cells(groups, 'h', IMPROVE),
              'limited_go_triggered': triggered_bootstrap(groups, iterations=a.iterations, seed=a.seed)}
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
