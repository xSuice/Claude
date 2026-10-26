"""M1a fixture integration: real D, MOCK read ports, no production effects.

Oracle/template stays in the host harness. Only public_state enters D/proposals.
No task store, scheduler, model client or operational authority is created.
A Python mock_proposer is trusted TEST CODE, not an OS isolation boundary.
"""
from copy import deepcopy
import deterministic_d as baseline
from branch_protocol import fork_fixture_case
from hybrid_evidence_gate import finalize_after_read
from host_adapter import guarded_check

ALLOWED_DIAGNOSES=frozenset({'service_healthy','dependency_not_running','config_value_invalid'}
                          |set(baseline.READINESS_REASONS)
                          |{cause for _,_,cause in baseline.CAPACITY_RULES})


def _diagnose(branch):
    state=branch.public_state()
    return baseline.diagnose(state['observations'],state['user_context'],step=state['reads_used'])


def run_d(branch):
    """Real D policy on a caller-owned MOCK port; no template/oracle access."""
    while True:
        result=_diagnose(branch)
        if result['status']=='VERIFIED_DIAGNOSIS' or branch.remaining<=0:
            return result
        selected=baseline.select_read(branch.public_state())
        if selected is None:
            return result
        branch.read(selected['tool'],selected['params'])


def run_pair(template, *, mock_proposer=None):
    # Fork BEFORE either policy spends a read. Preflight has no read port.
    fork=fork_fixture_case(template,baseline.preflight)
    d,h=fork['d'],fork['h']
    initial_receipt=_diagnose(d)
    d_result=run_d(d)
    out={'mode':'MOCK','trigger':fork['d_trigger'],'d':d_result,'h':deepcopy(d_result),
         'd_reads':d.reads_used,'h_reads':0,'d_snapshot_sha256':fork['snapshot_sha256'],
         'h_snapshot_sha256':None,'mock_proposal_calls':0,'real_model_calls':0,
         'A':'UNSUPPORTED','B':'NOT_RUN','events':[],
         'd_visible_ids':[o['id'] for o in d.public_state()['observations']],
         'h_visible_ids':[o['id'] for o in d.public_state()['observations']]}
    if h is None:
        return out
    assert h.snapshot_hash==d.snapshot_hash
    out['h_snapshot_sha256']=h.snapshot_hash
    out['h']=deepcopy(initial_receipt)
    if mock_proposer is None:
        out['h']=run_d(h)  # D fallback on H's OWN equal budget; no B attribution.
        out['events'].append({'decision':'D_FALLBACK_NO_B'})
    else:
        while h.remaining>0:
            state=h.public_state()
            out['mock_proposal_calls']+=1
            try:
                proposal=mock_proposer(deepcopy(state))
            except Exception:
                out['events'].append({'decision':'KEEP_D','reason':'MOCK_PROPOSER_ERROR'})
                break
            gate=guarded_check(fork['d_trigger'],proposal,state['observations'],
                step=state['reads_used'],allowed_tools=baseline.READ_TOOLS,
                tool_catalog=state['tool_catalog'],reads_used=state['reads_used'],
                read_budget=state['read_budget'],already_read=state['read_keys'])
            out['events'].append(deepcopy(gate))
            if gate['decision']!='SUGGEST_READ_ONLY':
                break
            pre_ids={o['id'] for o in state['observations']}
            revealed=h.read(gate['next_tool'],gate['next_params'])
            trusted=h.host_observations()
            def recheck(observations):
                public=[{k:v for k,v in o.items() if k!='reveal_on'} for o in observations]
                return baseline.diagnose(public,state['user_context'],step=h.reads_used)
            adopted=None
            for observation in revealed:
                final=finalize_after_read(gate,recheck,trusted_observations=trusted,
                    allowed_diagnoses=ALLOWED_DIAGNOSES,pre_read_observation_ids=pre_ids,
                    new_observation_id=observation['id'])
                out['events'].append(deepcopy(final))
                if final['decision']=='ADOPT_VERIFIED_D_RECHECK':
                    adopted=final
                    break
            if adopted is not None:
                out['h']={'status':'VERIFIED_DIAGNOSIS','cause_id':adopted['cause_id'],
                          'proof_observation_ids':list(adopted['proof_observation_ids'])}
                break
            if not revealed:
                out['events'].append({'decision':'KEEP_D','reason':'READ_REVEALED_NOTHING'})
    out['h_reads']=h.reads_used
    out['h_visible_ids']=[o['id'] for o in h.public_state()['observations']]
    return out

