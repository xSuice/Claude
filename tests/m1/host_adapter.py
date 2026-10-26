"""Offline input hardening around the unchanged public reference evidence gate.

Not an OS sandbox or production executor. The host supplies observations and
budgets; models never supply D callbacks, proof receipts, oracle or permissions.
"""
from copy import deepcopy
import hybrid_evidence_gate as reference


def reject(reason):
    return {'decision':'KEEP_D','reason':reason,'grounded':False}


def guarded_check(trigger,proposal,observations,**host):
    # Validate authority containers before Python membership/splat/hash operations.
    # In particular a string is not an allowlist and its substrings are not grants.
    required={'step','reads_used','read_budget','allowed_tools','tool_catalog'}
    if not required <= set(host) or set(host)-required-{'already_read'}:
        return reject('INVALID_HOST_FIELDS')
    if not isinstance(trigger,str):
        return reject('INVALID_TRIGGER_TYPE')
    collections=(list,tuple,set,frozenset)
    allowed=host['allowed_tools']
    history=host.get('already_read',())
    if (not isinstance(allowed,collections) or any(not isinstance(v,str) for v in allowed)
            or not isinstance(history,collections) or any(not isinstance(v,str) for v in history)):
        return reject('INVALID_HOST_AUTHORITY_OR_HISTORY')
    catalog=host['tool_catalog']
    if not isinstance(catalog,(list,tuple)):
        return reject('INVALID_HOST_CATALOG')
    for entry in catalog:
        if (not isinstance(entry,dict) or not isinstance(entry.get('tool'),str)
                or not isinstance(entry.get('params'),dict)):
            return reject('INVALID_HOST_CATALOG')
        for key,values in entry['params'].items():
            if (not isinstance(key,str) or not isinstance(values,collections)
                    or any(not isinstance(v,str) for v in values)):
                return reject('INVALID_HOST_CATALOG')
    if isinstance(observations,list) and any(isinstance(o,dict) and not isinstance(o.get('tool'),str) for o in observations):
        return reject('INVALID_OBSERVATION_PROVENANCE')
    if any(type(host.get(k)) is not int or host[k]<0 for k in ('step','reads_used','read_budget')):
        return reject('INVALID_TYPED_HOST_COUNTER')
    if isinstance(proposal,dict) and isinstance(proposal.get('claims'),list):
        if any(not isinstance(c,dict) or not isinstance(c.get('obs_id'),str) for c in proposal['claims']):
            return reject('INVALID_CLAIM_ID')
        ids=[c['obs_id'] for c in proposal['claims']]
        if len(ids)!=len(set(ids)):
            return reject('DUPLICATE_CLAIM_ID')
    if isinstance(observations, list) and any(
        isinstance(obs, dict) and (
            type(obs.get('available_at_step')) is not int
            or obs['available_at_step'] < 0
        )
        for obs in observations
    ):
        return reject('INVALID_OBSERVATION_STEP')
    return reference.check_proposal(trigger,deepcopy(proposal),deepcopy(observations),**host)
