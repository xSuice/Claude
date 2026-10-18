"""Offline input hardening around the unchanged public reference evidence gate.

Not an OS sandbox or production executor. The host supplies observations and
budgets; models never supply D callbacks, proof receipts, oracle or permissions.
"""
from copy import deepcopy
import hybrid_evidence_gate as reference


def reject(reason):
    return {'decision':'KEEP_D','reason':reason,'grounded':False}


def guarded_check(trigger,proposal,observations,**host):
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
