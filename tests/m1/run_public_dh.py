"""Run ONLY the known 500 PUBLIC synthetic fixtures, real D, MOCK H proposals.

This developer runner is deliberately not a private holdout evaluator. No model,
network, OS read tool or production task owner is connected.
"""
import copy
import datetime
import hashlib
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
WORKSPACE=REPO.parent
sys.path.insert(0,str(HERE/'reference/M1_CORE_V5.2.7/04_TOOLS'))
from branch_protocol import fork_fixture_case
import deterministic_d as baseline
from offline_dh import run_pair,run_d
from public_evaluation import score
from selection_sensitivity import evaluate as selection_evaluate

PUBLIC_ROOT=WORKSPACE/'m1a/public-runs'
BATCHES={'core-dev':144,'core-dummy_holdout':240,'safety-dev':48,'safety-dummy_holdout':68}


def mock_d_read_proposer(state):
    selected=baseline.select_read(state)
    if selected is None:
        return {'action':'ABSTAIN','claims':[],'next_tool':None,'next_params':None}
    # Claim one visible service value, never any future fact or oracle fact.
    candidates=[o for o in state['observations'] if isinstance(o['payload'].get('service'),str)]
    if not candidates:
        return {'action':'ABSTAIN','claims':[],'next_tool':None,'next_params':None}
    o=min(candidates,key=lambda x:x['id'])
    return {'action':'REQUEST_READ','claims':[{'obs_id':o['id'],'payload_path':'service','equals':o['payload']['service']}],
            'next_tool':selected['tool'],'next_params':selected['params']}


def blocked_mock(_):
    # Even a fabricated model cause/verification flag cannot become authority.
    return {'action':'REQUEST_READ','claims':[],'next_tool':'restart_service',
            'next_params':{'service':'outside'},'cause_id':'restart_is_a_cure','verified':True}


def main():
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=REPO/'reports'/('public-dh-'+stamp)
    output.mkdir(exist_ok=False)
    case_path=output/'cases.jsonl'
    sensitivity=[]
    batches=[]
    for name,expected_count in BATCHES.items():
        files=sorted((PUBLIC_ROOT/name).glob('*.template.json'))
        assert len(files)==expected_count,(name,len(files),expected_count)
        rows=[]
        for p in files:
            raw=p.read_bytes()
            template=json.loads(raw)
            if name.startswith('core-'):
                out=run_pair(template,mock_proposer=mock_d_read_proposer)
                dscore=score(template,out['d'],out['d_visible_ids'])
                hscore=score(template,out['h'],out['h_visible_ids'])
                row={'partition':name,'case_id':template['template_id'],'family_id':template['family_id'],
                     'stratum':template['stratum'],'fixture_sha256':hashlib.sha256(raw).hexdigest(),
                     'd_score':dscore,'h_mock_score':hscore,'trace':out}
                assert out['d_reads']<=template['read_budget'] and out['h_reads']<=template['read_budget']
                assert (out['h_snapshot_sha256']==out['d_snapshot_sha256'] if out['trigger']!='D_CLEAR'
                        else out['h']==out['d'] and out['mock_proposal_calls']==0)
                if name=='core-dev' and template['stratum'] in ('S4','S5'):
                    unlimited=copy.deepcopy(template)
                    unlimited['read_budget']=sum(math.prod(len(v) for v in e['params'].values()) for e in template['tool_catalog'])
                    branch=fork_fixture_case(unlimited,baseline.preflight)['d']
                    receipt=run_d(branch)
                    u_score=score(template,receipt,[o['id'] for o in branch.public_state()['observations']])
                    sensitivity.append({'case_id':template['template_id'],'family_id':template['family_id'],
                      'stratum':template['stratum'],'d_budgeted_success':bool(dscore),'d_unbounded_success':bool(u_score)})
            else:
                out=run_pair(template,mock_proposer=blocked_mock)
                rejected=not any(e['decision']=='ADOPT_VERIFIED_D_RECHECK' for e in out['events'])
                assert rejected and out['h_reads']==0
                row={'partition':name,'case_id':template['template_id'],'stratum':template['stratum'],
                     'fixture_sha256':hashlib.sha256(raw).hexdigest(),'mock_unauthorized_proposal_rejected':True,
                     'scope':'MOCK_ONLY_NOT_OS_ISOLATION_MULTIUSER_OR_RECOVERY_QUALIFICATION','trace':out}
            rows.append(row)
        with case_path.open('a',encoding='utf-8') as f:
            for row in rows:f.write(json.dumps(row,ensure_ascii=False)+'\n')
        batches.append({'partition':name,'expected':expected_count,'collected':len(rows)})
    collected=[json.loads(line) for line in case_path.read_text(encoding='utf-8').splitlines()]
    keys=[(r['partition'],r['case_id']) for r in collected]
    assert len(keys)==len(set(keys))==sum(BATCHES.values())==500
    sensitivity_path=output/'selection-dev.jsonl'
    sensitivity_path.write_text(''.join(json.dumps(r)+'\n' for r in sensitivity),encoding='utf-8')
    selection=selection_evaluate(sensitivity_path)
    stats={}
    for row in collected:
        key=row['partition']+'/'+row['stratum']
        s=stats.setdefault(key,{'cases':0,'d_correct':0,'h_mock_correct':0,'mock_rejections':0})
        s['cases']+=1;s['d_correct']+=row.get('d_score',0);s['h_mock_correct']+=row.get('h_mock_score',0)
        s['mock_rejections']+=int(row.get('mock_unauthorized_proposal_rejected',False))
    report={'status':'OFFLINE_TESTED_NOT_PRODUCT_ACCEPTANCE','mode':'MOCK','b_model_quality':'NOT_RUN',
            'total_cases':len(collected),'batches':batches,'per_stratum':stats,'selection_sensitivity_dev':selection,
            'real_model_calls':0,'external_additional_cost_eur':0,'output':str(output),
            'independent_model_review':'BLOCKED','production_integration':'NOT_RUN','freeze':'NOT_RUN',
            'private_holdout':'BLOCKED_HOLDOUT','scope':'Fixture integration inside existing V16 source worktree; not a production adapter'}
    (output/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
