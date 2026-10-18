#!/usr/bin/env python3
"""M1a reference contract for H; oracle-free, read-only suggestion stage (v5.2.5).

NOT a production sandbox and NOT a causality oracle. The host controls observation
provenance, the tool catalog, the read budget and D's independent post-read recheck.
A model never supplies verified/grounded flags.

What the gate guarantees (and what it does not):
  * B may only propose ONE read (tool + parameters from the host catalog) or abstain.
  * Cited claims must match payloads the host already made visible. This is a
    GROUNDING check: it shows B did not invent facts. It does NOT show relevance.
  * The final cause is only ever adopted via D's own recheck receipt, and that
    receipt must USE the observation B's read revealed (attribution).
"""
import json
import re

TRIGGERS = frozenset({'D_ABSTAIN', 'D_OBSERVATION_CONFLICT'})
READ_TOOLS = frozenset({'service_status', 'service_readiness', 'read_config', 'read_logs'})
PATH_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$')
PROPOSAL_KEYS = {'action', 'claims', 'next_tool', 'next_params'}


def read_key(tool, params):
    """Canonical key for a concrete read (same format as validate_fixture)."""
    return json.dumps([tool, sorted(params.items())], ensure_ascii=False)


def _reject(reason):
    return {'decision': 'KEEP_D', 'reason': reason, 'grounded': False}


def _read_path(payload, path):
    if not isinstance(path, str) or not PATH_RE.fullmatch(path):
        raise ValueError('invalid_payload_path')
    result = payload
    for part in path.split('.'):
        if not isinstance(result, dict) or part not in result:
            raise ValueError('missing_payload_path')
        result = result[part]
    return result


def _catalog_spec(tool_catalog, tool):
    for entry in tool_catalog:
        if isinstance(entry, dict) and entry.get('tool') == tool:
            return entry.get('params')
    return None


def check_proposal(d_trigger, proposal, observations, *, step, allowed_tools,
                   tool_catalog, reads_used, read_budget, already_read=()):
    """Check a model PROPOSAL (never a final answer) against host-captured observations.

    `observations` must contain only what the host has already made visible to B.
    `already_read` is an iterable of read_key() values that were executed before.
    """
    if d_trigger not in TRIGGERS:
        return _reject('D_DECIDES_NO_TRIGGER')
    if not isinstance(step, int) or step < 0:
        return _reject('INVALID_STEP')
    if not isinstance(proposal, dict) or set(proposal) != PROPOSAL_KEYS:
        return _reject('INVALID_PROPOSAL_SHAPE')
    action, claims = proposal['action'], proposal['claims']
    tool, params = proposal['next_tool'], proposal['next_params']
    if action not in ('REQUEST_READ', 'ABSTAIN') or not isinstance(claims, list):
        return _reject('UNSUPPORTED_ACTION')
    if not isinstance(observations, list):
        return _reject('INVALID_OBSERVATIONS')
    by_id = {}
    for obs in observations:
        if not isinstance(obs, dict) or not isinstance(obs.get('id'), str) or obs['id'] in by_id:
            return _reject('INVALID_OBSERVATION_OR_DUPLICATE_ID')
        by_id[obs['id']] = obs
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != {'obs_id', 'payload_path', 'equals'}:
            return _reject('INVALID_CLAIM_SHAPE')
        obs = by_id.get(claim['obs_id'])
        if obs is None:
            return _reject('UNKNOWN_OR_INACCESSIBLE_OBSERVATION')
        if not isinstance(obs.get('available_at_step'), int) or obs['available_at_step'] > step:
            return _reject('FUTURE_OR_INACCESSIBLE_OBSERVATION')
        if obs.get('tool') not in READ_TOOLS | {'tool_result'} or not isinstance(obs.get('payload'), dict):
            return _reject('INVALID_OBSERVATION_PROVENANCE')
        try:
            actual = _read_path(obs['payload'], claim['payload_path'])
        except (ValueError, KeyError, TypeError):
            return _reject('MISSING_OR_INVALID_OBSERVED_VALUE')
        if type(actual) is not type(claim['equals']) or actual != claim['equals']:
            return _reject('CLAIM_DOES_NOT_MATCH_PAYLOAD')
    if action == 'ABSTAIN':
        if tool is not None or params is not None:
            return _reject('ABSTAIN_CANNOT_REQUEST_TOOL')
        return _reject('B_ABSTAINS_D_PRESERVED')
    if not claims:
        return _reject('READ_SUGGESTION_REQUIRES_GROUNDED_CONTEXT')
    if not isinstance(tool, str) or tool not in READ_TOOLS or tool not in allowed_tools:
        return _reject('NOT_AUTHORIZED_READ_TOOL')
    if not isinstance(reads_used, int) or not isinstance(read_budget, int) or reads_used < 0:
        return _reject('INVALID_BUDGET_STATE')
    if reads_used >= read_budget:
        return _reject('READ_BUDGET_EXHAUSTED')
    spec = _catalog_spec(tool_catalog, tool)
    if not isinstance(spec, dict) or not isinstance(params, dict) or set(params) != set(spec):
        return _reject('INVALID_READ_PARAMETERS')
    for key, value in params.items():
        if not isinstance(value, str) or value not in spec[key]:
            return _reject('PARAMETER_VALUE_NOT_IN_CATALOG')
    key = read_key(tool, params)
    if key in set(already_read):
        return _reject('DUPLICATE_READ')
    return {'decision': 'SUGGEST_READ_ONLY', 'reason': 'CLAIMS_MATCH_VISIBLE_PAYLOAD',
            'grounded': True, 'next_tool': tool, 'next_params': dict(params), 'read_key': key}


def finalize_after_read(gate_result, d_recheck, *, trusted_observations, allowed_diagnoses,
                        pre_read_observation_ids, new_observation_id):
    """Adopt a cause ONLY via a host-provided D recheck that uses B's newly revealed observation.

    Returns ADOPT_VERIFIED_D_RECHECK only if
      * the read revealed a genuinely new observation matching exactly B's authorized read,
      * D (trusted, pinned, unreachable for B) returns a VERIFIED_DIAGNOSIS receipt, and
      * the receipt's proof ids exist and INCLUDE the new observation.
    Otherwise the original D abstention/conflict stays authoritative.
    """
    if not isinstance(gate_result, dict) or gate_result.get('decision') != 'SUGGEST_READ_ONLY':
        return _reject('NO_AUTHORIZED_READ_SUGGESTION')
    if not callable(d_recheck):
        return _reject('NO_TRUSTED_D_RECHECK')
    if new_observation_id is None:
        return _reject('READ_REVEALED_NOTHING')
    pre = set(pre_read_observation_ids)
    by_id = {o['id']: o for o in trusted_observations if isinstance(o, dict) and isinstance(o.get('id'), str)}
    new_obs = by_id.get(new_observation_id)
    if new_obs is None or new_observation_id in pre:
        return _reject('NEW_OBSERVATION_NOT_NEW_OR_UNKNOWN')
    reveal = new_obs.get('reveal_on')
    if not isinstance(reveal, dict) or read_key(reveal.get('tool'), reveal.get('params', {})) != gate_result['read_key']:
        return _reject('NEW_OBSERVATION_NOT_FROM_AUTHORIZED_READ')
    result = d_recheck(trusted_observations)
    if not isinstance(result, dict) or set(result) != {'status', 'cause_id', 'proof_observation_ids'}:
        return _reject('INVALID_D_RECHECK_RECEIPT')
    if result['status'] != 'VERIFIED_DIAGNOSIS' or result['cause_id'] not in allowed_diagnoses:
        return _reject('NO_VERIFIED_CAUSAL_PROOF')
    ids = result['proof_observation_ids']
    if (not isinstance(ids, list) or not ids or len(ids) != len(set(ids))
            or not all(isinstance(i, str) and i in by_id for i in ids)):
        return _reject('INVALID_OR_MISSING_D_PROOF_EVIDENCE')
    if new_observation_id not in ids:
        return _reject('D_PROOF_DOES_NOT_USE_NEW_OBSERVATION')
    return {'decision': 'ADOPT_VERIFIED_D_RECHECK', 'cause_id': result['cause_id'],
            'proof_observation_ids': ids, 'new_observation_id': new_observation_id,
            'd_verified': True}
