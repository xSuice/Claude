"""Public MOCK host-adapter tests. No model, network, private oracle or OS isolation claim."""
import importlib
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE/'reference/M1_CORE_V5.2.7/04_TOOLS'))
import hybrid_evidence_gate as reference

OBS=[{'id':'o1','tool':'service_status','available_at_step':0,'payload':{'ready':False}}]
CAT=[{'tool':'read_config','params':{'service':['db']}}]
PROPOSAL={'action':'REQUEST_READ','claims':[{'obs_id':'o1','payload_path':'ready','equals':False}],
          'next_tool':'read_config','next_params':{'service':'db'}}

def args():
    return dict(step=0,allowed_tools={'read_config'},tool_catalog=CAT,reads_used=0,read_budget=1)

class GuardedProposalTests(unittest.TestCase):
    def guarded(self):
        self.assertTrue((HERE/'host_adapter.py').is_file(),'Missing fail-closed host adapter')
        return importlib.import_module('host_adapter').guarded_check

    def test_unhashable_claim_id_is_rejected_instead_of_crashing(self):
        proposal={**PROPOSAL,'claims':[{'obs_id':[],'payload_path':'ready','equals':False}]}
        with self.assertRaises(TypeError):
            reference.check_proposal('D_ABSTAIN',proposal,OBS,**args())
        result=self.guarded()('D_ABSTAIN',proposal,OBS,**args())
        self.assertEqual(result['decision'],'KEEP_D')

    def test_boolean_host_counters_are_not_integers(self):
        for key in ('step','reads_used','read_budget'):
            with self.subTest(key=key):
                host=args(); host[key]=True if key!='reads_used' else False
                self.assertEqual(self.guarded()('D_ABSTAIN',PROPOSAL,OBS,**host)['decision'],'KEEP_D')

    def test_duplicate_claim_ids_fail_closed(self):
        proposal={**PROPOSAL,'claims':PROPOSAL['claims']*2}
        self.assertEqual(self.guarded()('D_ABSTAIN',proposal,OBS,**args())['decision'],'KEEP_D')

    def test_observation_steps_require_nonnegative_real_integers(self):
        for invalid in (False, True, -1, 0.0, '0', None):
            with self.subTest(available_at_step=invalid):
                observations = [{**OBS[0], 'available_at_step': invalid}]
                host = args()
                host['step'] = 2
                result = self.guarded()('D_ABSTAIN', PROPOSAL, observations, **host)
                self.assertEqual(result['decision'], 'KEEP_D')
                self.assertEqual(result['reason'], 'INVALID_OBSERVATION_STEP')

    def test_non_dict_observation_entries_fail_closed_in_composition(self):
        # Kimi-K3 review finding (non-blocking): non-dict list entries skip the
        # host step check by design; the composition must still fail closed at
        # the reference gate. Pin the composed KEEP_D, never a crash or pass.
        for bad in (None, 'x', 7, ['nested']):
            with self.subTest(entry=repr(bad)):
                result=self.guarded()('D_ABSTAIN',PROPOSAL,[dict(OBS[0]),bad] if bad is not None else None,**args())
                self.assertEqual(result['decision'],'KEEP_D')
                self.assertFalse(result['grounded'])
                if bad is None:
                    self.assertEqual(result['reason'],'INVALID_OBSERVATIONS')
                else:
                    self.assertEqual(result['reason'],'INVALID_OBSERVATION_OR_DUPLICATE_ID')

    def test_valid_read_is_preserved_without_executing_it(self):
        self.assertEqual(self.guarded()('D_ABSTAIN',PROPOSAL,OBS,**args()),
                         reference.check_proposal('D_ABSTAIN',PROPOSAL,OBS,**args()))
        self.assertEqual(OBS[0]['payload'],{'ready':False})

if __name__=='__main__':unittest.main()
