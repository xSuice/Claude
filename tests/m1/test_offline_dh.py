"""Synthetic integration tests; real D rules, reference fixture ports, NO inference."""
import copy
import importlib
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE/'reference/M1_CORE_V5.2.7/04_TOOLS'))
from test_deterministic_d import obs


def capacity_case():
    demand=obs('demand','read_config',pool_size=32)
    hidden=obs('limit','read_config','db',step=1,max_connections=20)
    hidden['reveal_on']={'tool':'read_config','params':{'service':'db'}}
    decoy=obs('decoy','read_config','proxy',step=1,max_connections=100)
    decoy['reveal_on']={'tool':'read_config','params':{'service':'proxy'}}
    return {'user_request':'Warum schlägt app fehl?','read_budget':1,
            'tool_catalog':[{'tool':'read_config','params':{'service':['app','db','proxy']}}],
            'observations':[demand,hidden,decoy],
            'oracle':{'must_never_be_passed_to_D_or_mock_B':True}}


def read_db(state):
    assert set(state)=={'user_context','observations','tool_catalog','read_budget','reads_used','read_keys'}
    assert {o['id'] for o in state['observations']}=={'demand'}
    return {'action':'REQUEST_READ','claims':[{'obs_id':'demand','payload_path':'pool_size','equals':32}],
            'next_tool':'read_config','next_params':{'service':'db'}}


class OfflineDHTests(unittest.TestCase):
    def driver(self):
        self.assertTrue((HERE/'offline_dh.py').is_file(),'Missing actual D/H fixture driver')
        return importlib.import_module('offline_dh')

    def test_clear_preflight_is_literal_h_equals_d_without_B(self):
        driver=self.driver()
        case=capacity_case()
        case['observations']=[obs('status','service_status',state='running'),obs('ready','service_readiness',state='ready')]
        def forbidden(_):
            self.fail('B called without a D trigger')
        out=driver.run_pair(case,mock_proposer=forbidden)
        self.assertEqual(out['trigger'],'D_CLEAR')
        self.assertEqual(out['d'],out['h'])
        self.assertEqual(out['mock_proposal_calls'],0)
        self.assertEqual(out['d_reads'],0)
        self.assertIsNone(out['h_snapshot_sha256'])


    def test_triggered_paths_use_independent_full_budgets_and_new_d_proof(self):
        driver=self.driver()
        case=capacity_case();before=copy.deepcopy(case)
        out=driver.run_pair(case,mock_proposer=read_db)
        self.assertEqual(out['trigger'],'D_ABSTAIN')
        self.assertEqual(out['d_reads'],1)
        self.assertEqual(out['h_reads'],1)
        self.assertEqual(out['d_snapshot_sha256'],out['h_snapshot_sha256'])
        self.assertEqual(out['d']['cause_id'],'connection_limit_below_pool')
        self.assertEqual(out['h'],out['d'])
        self.assertEqual(out['mock_proposal_calls'],1)
        self.assertEqual(out['events'][-1]['decision'],'ADOPT_VERIFIED_D_RECHECK')
        self.assertEqual(set(out['h']['proof_observation_ids']),{'demand','limit'})
        self.assertEqual(case,before)


    def test_wrong_h_read_cannot_borrow_d_branch_evidence(self):
        driver=self.driver()
        def wrong(state):
            p=read_db(state);p['next_params']['service']='proxy';return p
        out=driver.run_pair(capacity_case(),mock_proposer=wrong)
        self.assertEqual(out['d']['status'],'VERIFIED_DIAGNOSIS')
        self.assertEqual(out['h']['status'],'ABSTAIN')
        self.assertNotIn('limit',out['h_visible_ids'])
        self.assertEqual(out['h_reads'],1)
        self.assertTrue(all(e['decision']!='ADOPT_VERIFIED_D_RECHECK' for e in out['events']))

    def test_model_supplied_verified_flags_or_cause_are_rejected(self):
        driver=self.driver()
        for extra in ({'verified':True},{'cause_id':'connection_limit_below_pool'},{'d_verified':True}):
            def forged(state):
                p=read_db(state);p.update(extra);return p
            out=driver.run_pair(capacity_case(),mock_proposer=forged)
            self.assertEqual(out['h']['status'],'ABSTAIN')
            self.assertEqual(out['h_reads'],0)
            self.assertEqual(out['events'][-1]['reason'],'INVALID_PROPOSAL_SHAPE')

    def test_mutating_model_view_cannot_change_host_evidence(self):
        driver=self.driver()
        def tamper(state):
            state['observations'][0]['payload']['pool_size']=999
            p=read_db(state);p['claims'][0]['equals']=999;return p
        out=driver.run_pair(capacity_case(),mock_proposer=tamper)
        self.assertEqual(out['h_reads'],0)
        self.assertEqual(out['events'][-1]['reason'],'CLAIM_DOES_NOT_MATCH_PAYLOAD')

    def test_unauthorized_action_and_hidden_claim_never_execute(self):
        driver=self.driver()
        for bad in ('write','hidden','unknown_param'):
            def attack(state):
                p=read_db(state)
                if bad=='write':p['next_tool']='restart_service'
                if bad=='hidden':p['claims'][0]['obs_id']='limit'
                if bad=='unknown_param':p['next_params']['service']='outside'
                return p
            out=driver.run_pair(capacity_case(),mock_proposer=attack)
            self.assertEqual(out['h_reads'],0)
            self.assertEqual(out['h']['status'],'ABSTAIN')

    def test_failed_mock_and_zero_budget_are_bounded(self):
        driver=self.driver()
        def crash(_):raise RuntimeError('synthetic failure')
        out=driver.run_pair(capacity_case(),mock_proposer=crash)
        self.assertEqual(out['mock_proposal_calls'],1)
        self.assertEqual(out['h_reads'],0)
        case=capacity_case();case['read_budget']=0
        out=driver.run_pair(case,mock_proposer=crash)
        self.assertEqual(out['mock_proposal_calls'],0)
        self.assertEqual(out['d_reads'],0)

    def test_missing_B_fallback_spends_only_h_own_budget(self):
        out=self.driver().run_pair(capacity_case())
        self.assertEqual(out['d'],out['h'])
        self.assertEqual(out['d_reads'],1)
        self.assertEqual(out['h_reads'],1)
        self.assertEqual(out['mock_proposal_calls'],0)


    def test_public_evaluator_rejects_padding_hidden_ids_and_false_status(self):
        self.assertTrue((HERE/'public_evaluation.py').is_file(),'Missing evaluator-only scoring')
        score=importlib.import_module('public_evaluation').score
        case=capacity_case();case['oracle']={'expected_resolution':'diagnose',
             'root_cause_id':'connection_limit_below_pool','required_proof_sets':[['demand','limit']]}
        receipt={'status':'VERIFIED_DIAGNOSIS','cause_id':'connection_limit_below_pool',
                 'proof_observation_ids':['limit','demand']}
        self.assertEqual(score(case,receipt,['demand','limit']),1)
        for bad in (dict(receipt,status='ABSTAIN'),dict(receipt,proof_observation_ids=['demand','limit','decoy']),
                    dict(receipt,**{'pass':False})):
            self.assertEqual(score(case,bad,['demand','limit','decoy']),0)
        self.assertEqual(score(case,receipt,['demand']),0)


    def test_health_score_requires_actual_target_status_and_readiness(self):
        score=importlib.import_module('public_evaluation').score
        case={'user_request':'Prüfe app','oracle':{'expected_resolution':'healthy'},
              'observations':[obs('log','read_logs',lines=['INFO fine']),
                              obs('status','service_status',state='running'),obs('ready','service_readiness',state='ready')]}
        receipt={'status':'VERIFIED_DIAGNOSIS','cause_id':'service_healthy','proof_observation_ids':['log']}
        self.assertEqual(score(case,receipt,['log','status','ready']),0)
        receipt['proof_observation_ids']=['status','ready']
        self.assertEqual(score(case,receipt,['log','status','ready']),1)
        case['observations'][2]['payload']['state']='not_ready'
        self.assertEqual(score(case,receipt,['log','status','ready']),0)


if __name__=='__main__':
    unittest.main()
