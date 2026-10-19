"""EVALUATOR ONLY, explicitly PUBLIC synthetic fixtures. Never imported by D/H.

No private data is loaded by this module. Caller must not use private holdouts in
this developer environment. A successful fixture score is not real-world causality.
"""
from validate_fixture import oracle_proof_satisfied


def score(template, receipt, visible_ids):
    if not isinstance(receipt,dict) or set(receipt)!={'status','cause_id','proof_observation_ids'}:
        return 0
    ids=receipt['proof_observation_ids']
    if (not isinstance(ids,list) or any(not isinstance(i,str) for i in ids)
            or len(ids)!=len(set(ids)) or not set(ids).issubset(set(visible_ids))):
        return 0
    expected=template['oracle']['expected_resolution']
    if expected=='diagnose':
        return int(receipt['status']=='VERIFIED_DIAGNOSIS' and oracle_proof_satisfied(
            template,receipt['cause_id'],ids,visible_observation_ids=visible_ids))
    if expected=='healthy':
        if receipt['status']!='VERIFIED_DIAGNOSIS' or receipt['cause_id']!='service_healthy' or len(ids)!=2:
            return 0
        by_id={o['id']:o for o in template['observations']}
        evidence=[by_id[i] for i in ids if i in by_id]
        statuses=[o for o in evidence if o['tool']=='service_status' and o['payload'].get('state')=='running']
        ready=[o for o in evidence if o['tool']=='service_readiness' and o['payload'].get('state')=='ready']
        if len(statuses)!=1 or len(ready)!=1:
            return 0
        service=statuses[0]['payload'].get('service')
        if not isinstance(service,str) or service!=ready[0]['payload'].get('service'):
            return 0
        import re
        return int(bool(re.search(r'(?<![\w-])'+re.escape(service)+r'(?![\w-])',template['user_request'])))
    if expected=='abstain':
        return int(receipt['status'] in ('ABSTAIN','OBSERVATION_CONFLICT') and receipt['cause_id'] is None)
    return 0
