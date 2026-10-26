#!/usr/bin/env python3
"""Validate public dummy or PRIVATE evaluator template contract.
Requires jsonschema; do not share private templates with Claude Code.
"""
import argparse
import json
from pathlib import Path
from datetime import datetime


SELECTION_STRATA = ('S4', 'S5')


def _read_key(tool, params):
    return json.dumps([tool, sorted(params.items())], ensure_ascii=False)


def _catalog_options(catalog):
    """All concrete read options (tool x full parameter combinations)."""
    options = set()
    for entry in catalog:
        keys = sorted(entry['params'])
        combos = [{}]
        for k in keys:
            combos = [dict(c, **{k: v}) for c in combos for v in entry['params'][k]]
        for c in combos:
            options.add(_read_key(entry['tool'], c))
    return options


def _check_catalog_and_budget(template):
    catalog = template['tool_catalog']
    by_tool = {}
    for entry in catalog:
        if entry['tool'] in by_tool:
            raise ValueError(f"tool_catalog: Tool {entry['tool']} doppelt")
        by_tool[entry['tool']] = entry['params']
    options = _catalog_options(catalog)
    budget = template['read_budget']
    hidden_keys = set()
    hidden_by_id = {}
    for obs in template['observations']:
        rev = obs.get('reveal_on')
        if rev is None:
            continue
        spec = by_tool.get(rev['tool'])
        if spec is None:
            raise ValueError(f"Observation {obs['id']}: reveal_on-Tool nicht im tool_catalog")
        if set(rev['params']) != set(spec):
            raise ValueError(f"Observation {obs['id']}: reveal_on-Parameter müssen exakt {sorted(spec)} sein")
        for k, v in rev['params'].items():
            if v not in spec[k]:
                raise ValueError(f"Observation {obs['id']}: Wert {v!r} für {k} nicht im Katalog")
        key = _read_key(rev['tool'], rev['params'])
        hidden_keys.add(key)
        hidden_by_id[obs['id']] = key
    # A budget of zero is only meaningful when nothing is hidden.
    if budget == 0 and hidden_keys:
        raise ValueError('read_budget=0, aber versteckte Beobachtungen vorhanden')
    if template['stratum'] in SELECTION_STRATA:
        proof_sets = template['oracle']['required_proof_sets']
        feasible = []
        for evidence_set in proof_sets:
            required = {hidden_by_id[i] for i in evidence_set if i in hidden_by_id}
            if required and len(required) <= budget:
                feasible.append(required)
        if not feasible:
            if any(any(i in hidden_by_id for i in proof) for proof in proof_sets):
                raise ValueError('SELECTION_UNSOLVABLE: keine vollstaendige Belegkombination passt ins Lesebudget')
            raise ValueError('SELECTION_TRIVIAL: Kein relevanter Beleg ist versteckt (S4/S5 brauchen mindestens einen)')
        if len(hidden_keys) <= budget:
            raise ValueError('SELECTION_TRIVIAL: D könnte alle versteckten Beobachtungen lesen (Budget >= versteckte Reads)')
        if len(options) <= budget:
            raise ValueError('SELECTION_TRIVIAL: Katalog hat nicht mehr Optionen als das Budget')


def validate(schema_path, template_path):
    import jsonschema
    schema = json.loads(Path(schema_path).read_text(encoding='utf-8'))
    template = json.loads(Path(template_path).read_text(encoding='utf-8'))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    issues = sorted(validator.iter_errors(template), key=lambda e: str(e.path))
    if issues:
        raise ValueError('; '.join(f"{list(e.path)}: {e.message}" for e in issues))
    # Explicit RFC3339-ish aware timestamp check; jsonschema format checkers may
    # silently skip unknown formats when optional dependencies are unavailable.
    for obs in template['observations']:
        # An observation must be initial or have an explicit authorized read that
        # can reveal it. Otherwise the branch executor silently drops it.
        if 'reveal_on' not in obs and obs['available_at_step'] != 0:
            raise ValueError(f"ORPHAN_OBSERVATION: {obs['id']} has no reveal_on and is not initially available")
        raw = obs['captured_at']
        try:
            parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ValueError('timezone required')
        except (ValueError, TypeError) as e:
            raise ValueError(f"Observation {obs['id']}: captured_at requires timezone-aware ISO8601") from e
    _check_catalog_and_budget(template)
    ids = [x['id'] for x in template['observations']]
    if len(set(ids)) != len(ids):
        raise ValueError('Observation-IDs dürfen nicht doppelt vorkommen')
    proof_sets = template['oracle']['required_proof_sets']
    if not all(set(proof).issubset(ids) for proof in proof_sets):
        raise ValueError('Oracle-Proof-Set verweist auf nicht vorhandene Observation-ID')
    expected = template['oracle']['expected_resolution']
    if expected == 'diagnose':
        if not template['oracle']['root_cause_id'] or not proof_sets:
            raise ValueError('DIAGNOSE_REQUIRES_CAUSE_AND_COMPLETE_PROOF_SET')
    elif proof_sets:
        raise ValueError('NON_DIAGNOSIS_MUST_NOT_REQUIRE_CAUSAL_PROOF_SETS')
    return True


def oracle_proof_satisfied(template, cause_id, proof_observation_ids, *, visible_observation_ids):
    """Evaluator only: an asserted cause needs EVERY ID of an independent sufficient set.

    Proof IDs must match exactly one independent sufficient set (no extra IDs).
    Matching IDs establishes an evidence-set condition, NOT causality by itself.
    This function MUST never run in the model/controller/production authority path.
    """
    oracle = template['oracle']
    ids = proof_observation_ids
    if (oracle['expected_resolution'] != 'diagnose'
            or not isinstance(cause_id, str) or cause_id != oracle['root_cause_id']
            or not isinstance(ids, list) or any(not isinstance(i, str) for i in ids)
            or len(set(ids)) != len(ids)):
        return False
    if not isinstance(visible_observation_ids, (list, tuple, set)) or any(
            not isinstance(i, str) for i in visible_observation_ids):
        return False
    supplied = set(ids)
    if not supplied.issubset(set(visible_observation_ids)):
        return False  # hidden or unrevealed evidence is NOT proof
    # Evaluation policy v5.2.7: no padding with unrelated observations.
    # Every submitted proof MUST match exactly one independently specified
    # sufficient set. Ordering is irrelevant, but extras are not permitted.
    return any(set(required) == supplied for required in oracle['required_proof_sets'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--schema', required=True)
    ap.add_argument('--template', required=True)
    args = ap.parse_args()
    try:
        validate(args.schema, args.template)
    except (ValueError, ImportError) as e:
        raise SystemExit(f'INVALID: {e}') from e
    print('VALID: format + evidence references; no clinical/security or causal correctness claimed')
