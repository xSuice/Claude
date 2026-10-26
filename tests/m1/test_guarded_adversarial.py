"""Public offline boundary tests; checking a read proposal never performs a read."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import unittest
from test_host_adapter import OBS, PROPOSAL, args
from host_adapter import guarded_check


class GuardedHostBoundaryTests(unittest.TestCase):
    def call(self, host=None, proposal=None, observations=None, trigger='D_ABSTAIN'):
        return guarded_check(trigger, deepcopy(PROPOSAL) if proposal is None else proposal,
                             deepcopy(OBS) if observations is None else observations,
                             **(args() if host is None else host))

    def test_missing_host_authority_fails_closed(self):
        for key in ('allowed_tools', 'tool_catalog'):
            host = args()
            del host[key]
            self.assertEqual(self.call(host)['decision'], 'KEEP_D')

    def test_invalid_read_history_fails_closed(self):
        for bad in (None, [[1]], [False], 2):
            with self.subTest(bad=bad):
                self.assertEqual(self.call({**args(), 'already_read': bad})['decision'], 'KEEP_D')

    def test_permissions_are_not_substring_authority(self):
        self.assertEqual(self.call({**args(), 'allowed_tools': 'read_config_extra'})['decision'], 'KEEP_D')

    def test_catalog_parameter_values_are_not_substrings(self):
        p = deepcopy(PROPOSAL)
        p['next_params'] = {'service': 'd'}
        host = {**args(), 'tool_catalog': [{'tool': 'read_config', 'params': {'service': 'db'}}]}
        self.assertEqual(self.call(host, proposal=p)['decision'], 'KEEP_D')

    def test_invalid_trigger_and_provenance_fails_closed(self):
        self.assertEqual(self.call(trigger=[])['decision'], 'KEEP_D')
        obs = deepcopy(OBS)
        obs[0]['tool'] = []
        self.assertEqual(self.call(observations=obs)['decision'], 'KEEP_D')

    def test_stale_budget_and_revoked_permissions_rechecked_on_each_check(self):
        self.assertEqual(self.call()['decision'], 'SUGGEST_READ_ONLY')
        for host in ({**args(), 'allowed_tools': set()}, {**args(), 'reads_used': 1}):
            self.assertEqual(self.call(host)['decision'], 'KEEP_D')

    def test_repeated_parallel_checks_neither_consume_reads_nor_mutate_inputs(self):
        p, o, h = deepcopy(PROPOSAL), deepcopy(OBS), args()
        original = deepcopy((p, o, h))
        def check(_):
            return guarded_check('D_ABSTAIN', p, o, **h)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(check, range(20)))
        self.assertTrue(all(r == results[0] for r in results))
        self.assertEqual((p, o, h), original)
        self.assertEqual(h['reads_used'], 0)

    def test_already_read_known_resource_is_rejected(self):
        key = self.call()['read_key']
        self.assertEqual(self.call({**args(), 'already_read': [key]})['reason'], 'DUPLICATE_READ')

    def test_future_unknown_and_unsupported_claims(self):
        for ident, step in (('missing', 0), ('o1', 1)):
            obs = deepcopy(OBS)
            obs[0]['available_at_step'] = step
            p = deepcopy(PROPOSAL)
            p['claims'][0]['obs_id'] = ident
            self.assertEqual(self.call(proposal=p, observations=obs)['decision'], 'KEEP_D')


if __name__ == '__main__':
    unittest.main(verbosity=2)
