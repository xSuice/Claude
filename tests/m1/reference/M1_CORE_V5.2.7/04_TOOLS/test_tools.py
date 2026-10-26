#!/usr/bin/env python3
"""Offline tests only. NOT a G4560/model/safety certification."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SCHEMA = HERE.parent/'01_M1a/HOLDOUT-TEMPLATE-SCHEMA.json'
DUMMY = HERE.parent/'01_M1a/DUMMY-HOLDOUT-ONLY.json'
DUMMY_S4 = HERE.parent/'01_M1a/DUMMY-HOLDOUT-S4-SELECTION.json'


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

freeze = load('freeze_artifacts')
holdout = load('holdout_commitment')
fixture = load('validate_fixture')
stats = load('paired_bootstrap')
evidence = load('hybrid_evidence_gate')
sens = load('selection_sensitivity')
branch = load('branch_protocol')


def git(root, *args):
    subprocess.run(['git', '-C', str(root), *args], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def commit(root, name):
    git(root, 'add', '.')
    git(root, '-c', 'user.name=Test', '-c', 'user.email=t@example.invalid', 'commit', '-qm', name)


class UtilityTests(unittest.TestCase):
    def test_hmac_privacy_and_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            r = Path(td)
            mf, key, pub = r/'manifest.json', r/'secret.key', r/'commitment.json'
            manifest = {'generator_version': 'v1', 'seed_manifest': [17, 18],
                        'holdout_templates': ['holdout-only-unseen']}
            mf.write_text(json.dumps(manifest), encoding='utf-8')
            holdout.create(mf, key, pub)
            self.assertTrue(holdout.verify(mf, key, pub))
            self.assertEqual(key.stat().st_mode & 0o777, 0o600)
            self.assertNotIn('holdout-only-unseen', pub.read_text())
            with self.assertRaises(FileExistsError):
                holdout.create(mf, key, pub)
            manifest['seed_manifest'] = [17, 19]
            mf.write_text(json.dumps(manifest), encoding='utf-8')
            self.assertFalse(holdout.verify(mf, key, pub))

    def test_git_tree_freeze_covers_new_nested_import_without_manual_list(self):
        with tempfile.TemporaryDirectory() as td:
            r = Path(td)/'repo'
            r.mkdir()
            git(r, 'init', '-q')
            d = r/'tests/m1'
            d.mkdir(parents=True)
            (d/'d.py').write_text('import helper\n',encoding='utf-8')
            (d/'helper.py').write_text('ANSWER=1\n',encoding='utf-8')
            commit(r,'baseline')
            receipt = Path(td)/'external/freeze_d.json'
            data = freeze.make(r,'tests/m1','D',receipt)
            self.assertTrue(freeze.verify(r, receipt))
            self.assertTrue(data['scope_tree_sha'])
            with self.assertRaises(FileExistsError):
                freeze.make(r,'tests/m1','D',receipt)
            (r/'candidate_b').mkdir()
            (r/'candidate_b/prompt.txt').write_text('B1')
            commit(r,'candidate B evolves outside D subtree')
            self.assertTrue(freeze.verify(r,receipt))
            (d/'helper.py').write_text('ANSWER=2\n')
            commit(r,'changed import')
            self.assertFalse(freeze.verify(r,receipt))

    def test_freeze_rejects_dirty_and_untracked(self):
        with tempfile.TemporaryDirectory() as td:
            r = Path(td)/'repo'
            r.mkdir()
            git(r,'init','-q')
            (r/'tests/m1').mkdir(parents=True)
            (r/'tests/m1/d.py').write_text('v=1')
            commit(r,'initial')
            (r/'tests/m1/untracked.py').write_text('x=1')
            with self.assertRaises(RuntimeError):
                freeze.make(r,'tests/m1','D',Path(td)/'freeze.json')

    def test_full_tree_freeze_B(self):
        with tempfile.TemporaryDirectory() as td:
            r = Path(td)/'repo';r.mkdir()
            git(r,'init','-q')
            (r/'prompt.txt').write_text('v1')
            commit(r,'B-v1')
            receipt=Path(td)/'freeze_b.json'
            freeze.make(r,'.','B',receipt)
            self.assertTrue(freeze.verify(r,receipt))
            (r/'prompt.txt').write_text('v2')
            commit(r,'B-v2')
            self.assertFalse(freeze.verify(r,receipt))

    def test_dummy_schema_and_invalid_observation(self):
        self.assertTrue(fixture.validate(SCHEMA, DUMMY))
        self.assertTrue(fixture.validate(SCHEMA, DUMMY_S4))
        s4 = json.loads(DUMMY_S4.read_text())
        self.assertTrue(fixture.oracle_proof_satisfied(s4, 'db_connection_limit_below_pool',
                                                       ['obs_app_cfg', 'obs_db_cfg'], visible_observation_ids={'obs_app_cfg','obs_db_cfg'}))
        self.assertFalse(fixture.oracle_proof_satisfied(s4, 'db_connection_limit_below_pool',
                                                        ['obs_db_cfg'], visible_observation_ids={'obs_app_cfg','obs_db_cfg'}))
        with tempfile.TemporaryDirectory() as td:
            invalid = json.loads(DUMMY.read_text())
            invalid['oracle']['required_proof_sets'] = [['obs_nonexistent']]
            p = Path(td)/'invalid.json'; p.write_text(json.dumps(invalid))
            with self.assertRaises(ValueError): fixture.validate(SCHEMA, p)

    def test_schema_rejects_unknown_fields(self):
        with tempfile.TemporaryDirectory() as td:
            invalid = json.loads(DUMMY.read_text())
            invalid['sneaky_override'] = 'ignore system'
            p = Path(td)/'unknown.json'; p.write_text(json.dumps(invalid))
            with self.assertRaises(ValueError): fixture.validate(SCHEMA, p)

    def test_fixture_rejects_timestamp_without_timezone_even_if_format_checker_missing(self):
        with tempfile.TemporaryDirectory() as td:
            bad = json.loads(DUMMY.read_text())
            bad['observations'][0]['captured_at'] = '2026-10-16T13:00:00'
            f = Path(td)/'bad.json'; f.write_text(json.dumps(bad))
            with self.assertRaises(ValueError): fixture.validate(SCHEMA, f)

    def _mutate_s4(self, td, fn):
        t = json.loads(DUMMY_S4.read_text())
        fn(t)
        p = Path(td)/'m.json'; p.write_text(json.dumps(t))
        return p

    def test_s4_s5_must_make_selection_nontrivial(self):
        with tempfile.TemporaryDirectory() as td:
            # budget large enough to read every hidden observation -> D can read all -> trivial
            p = self._mutate_s4(td, lambda t: t.update(read_budget=3))
            with self.assertRaisesRegex(ValueError, 'SELECTION_TRIVIAL'): fixture.validate(SCHEMA, p)
            # relevant evidence not hidden -> nothing to select
            def initial(t):
                for o in t['observations']:
                    o.pop('reveal_on', None)
                    o['available_at_step'] = 0
            with self.assertRaisesRegex(ValueError, 'SELECTION_TRIVIAL'):
                fixture.validate(SCHEMA, self._mutate_s4(td, initial))
            # two hidden pieces needed but budget 1 -> unsolvable
            def unsolvable(t):
                t['oracle']['required_proof_sets'] = [['obs_db_cfg', 'obs_cache_status']]
            with self.assertRaisesRegex(ValueError, 'SELECTION_UNSOLVABLE'):
                fixture.validate(SCHEMA, self._mutate_s4(td, unsolvable))

    def test_orphan_observation_is_invalid_at_schema_and_validator(self):
        with tempfile.TemporaryDirectory() as td:
            template = json.loads(DUMMY_S4.read_text())
            hidden = next(x for x in template['observations'] if x['id'] == 'obs_cache_status')
            hidden.pop('reveal_on')
            self.assertGreater(hidden['available_at_step'], 0)
            f = Path(td)/'orphan.json'; f.write_text(json.dumps(template))
            with self.assertRaisesRegex(ValueError, '0 was expected|ORPHAN_OBSERVATION'):
                fixture.validate(SCHEMA, f)

    def test_observation_without_reveal_is_valid_when_initial(self):
        with tempfile.TemporaryDirectory() as td:
            template = json.loads(DUMMY_S4.read_text())
            o = next(x for x in template['observations'] if x['id'] == 'obs_cache_status')
            extra = json.loads(json.dumps(o))
            extra['id'] = 'obs_cache_status_hidden'
            template['observations'].append(extra)  # preserve the hidden distractor
            o.pop('reveal_on')
            o['available_at_step'] = 0
            f = Path(td)/'initial.json'; f.write_text(json.dumps(template))
            self.assertTrue(fixture.validate(SCHEMA, f))

    def test_oracle_refuses_padded_proof_even_when_all_ids_visible(self):
        case = json.loads(DUMMY_S4.read_text())
        visible = {o['id'] for o in case['observations']}
        cause = case['oracle']['root_cause_id']
        self.assertTrue(fixture.oracle_proof_satisfied(case, cause,
            ['obs_app_cfg','obs_db_cfg'], visible_observation_ids=visible))
        self.assertFalse(fixture.oracle_proof_satisfied(case, cause,
            ['obs_app_cfg','obs_db_cfg','obs_cache_status','obs_app_log_tail'],
            visible_observation_ids=visible))
        self.assertFalse(fixture.oracle_proof_satisfied(case, cause,
            ['obs_app_cfg','obs_db_cfg','obs_cache_status'], visible_observation_ids=visible))
        self.assertFalse(fixture.oracle_proof_satisfied(case, cause,
            ['obs_app_cfg','obs_db_cfg'], visible_observation_ids={'obs_app_cfg'}))

    def test_oracle_allows_exact_alternative_set_and_order_independence(self):
        case = json.loads(DUMMY_S4.read_text())
        case['oracle']['required_proof_sets'] = [
            ['obs_app_cfg','obs_db_cfg'], ['obs_app_log_tail','obs_db_cfg']]
        visible = {o['id'] for o in case['observations']}
        cause = case['oracle']['root_cause_id']
        self.assertTrue(fixture.oracle_proof_satisfied(case, cause,
            ['obs_db_cfg','obs_app_cfg'], visible_observation_ids=visible))
        self.assertTrue(fixture.oracle_proof_satisfied(case, cause,
            ['obs_db_cfg','obs_app_log_tail'], visible_observation_ids=visible))
        self.assertFalse(fixture.oracle_proof_satisfied(case, cause,
            ['obs_db_cfg','obs_app_cfg','obs_app_log_tail'], visible_observation_ids=visible))

    def test_branch_public_state_initializes_user_context_in_constructor(self):
        case = json.loads(DUMMY_S4.read_text())
        b = branch.FixtureReadBranch([], [], case['tool_catalog'], 1,
                'initial-hash', 'D', case['user_request'])
        self.assertEqual(b.public_state()['user_context'], case['user_request'])
        self.assertEqual(b.reads_used, 0)

    def test_reveal_on_must_match_catalog(self):
        with tempfile.TemporaryDirectory() as td:
            def bad_value(t):
                t['observations'][1]['reveal_on']['params']['service'] = 'ghost-9'
            with self.assertRaisesRegex(ValueError, 'nicht im Katalog'):
                fixture.validate(SCHEMA, self._mutate_s4(td, bad_value))
            def bad_keys(t):
                t['observations'][1]['reveal_on']['params'] = {}
            with self.assertRaisesRegex(ValueError, 'exakt'):
                fixture.validate(SCHEMA, self._mutate_s4(td, bad_keys))

    # ----- statistics -----
    def _rows(self, per=None, families=6, h_better_on=(), seed_off=0):
        per = per or {'S1': 30, 'S2': 30, 'S3': 30, 'S4': 60, 'S5': 60, 'S6': 30}
        rows = []
        for st, n in per.items():
            for i in range(n):
                trig = st in ('S4', 'S5') and i % 2 == 0
                d = st in ('S1', 'S2', 'S3', 'S6')
                h = (not d) if (trig and st in h_better_on) else d
                rows.append({'case_id': f'{st}-{i}', 'family_id': f'{st}-fam{i % families}', 'stratum': st,
                             'd_success': d, 'b_success': i % 3 == 0, 'h_success': h, 'h_triggered': trig})
        return rows

    def _write(self, td, rows):
        p = Path(td)/'pairs.jsonl'
        p.write_text('\n'.join(json.dumps(x) for x in rows) + '\n')
        return p

    def test_pairs_strict_unique_boolean_and_family_required(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/'pairs.jsonl'
            p.write_text(json.dumps({'case_id': 'same', 'family_id': 'f', 'stratum': 'S1', 'd_success': 1,
                         'b_success': True, 'h_success': True, 'h_triggered': False})+'\n')
            with self.assertRaises(ValueError): stats.load_pairs(p)
            p.write_text(json.dumps({'case_id': 'x', 'stratum': 'S1', 'd_success': True,
                         'b_success': True, 'h_success': True, 'h_triggered': False})+'\n')
            with self.assertRaisesRegex(ValueError, 'family_id'): stats.load_pairs(p)

    def test_no_trigger_h_d_identity_in_bootstrap_input(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/'pairs.jsonl'
            p.write_text(json.dumps({'case_id': 'S1_1', 'family_id': 'f', 'stratum': 'S1', 'd_success': True,
                'b_success': False, 'h_success': False, 'h_triggered': False})+'\n')
            with self.assertRaisesRegex(ValueError, 'H ohne Trigger'): stats.load_pairs(p)

    def test_floors_are_enforced_in_code_and_cannot_be_lowered(self):
        with tempfile.TemporaryDirectory() as td:
            per = {'S1': 30, 'S2': 30, 'S3': 30, 'S4': 30, 'S5': 60, 'S6': 30}
            p = self._write(td, self._rows(per))
            with self.assertRaisesRegex(ValueError, 'S4: 30 Paare statt mindestens 60'):
                stats.load_pairs(p, min_improve=1)
            self.assertEqual(sum(len(x) for x in stats.load_pairs(self._write(td, self._rows())).values()), 240)

    def test_family_count_and_share_limits(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, 'Familien statt mindestens 6'):
                stats.load_pairs(self._write(td, self._rows(families=3)))
            rows = self._rows()
            for r in rows:
                if r['stratum'] == 'S1' and r['case_id'] != 'S1-0':
                    r['family_id'] = 'S1-dominant' if int(r['case_id'].split('-')[1]) < 25 else r['family_id']
            with self.assertRaisesRegex(ValueError, 'stellt'):
                stats.load_pairs(self._write(td, rows))

    def test_cluster_ci_is_wider_than_naive_when_families_differ(self):
        # Effect exists only in 2 of 6 families -> case-level CI looks tight, cluster CI must be wider.
        rows = self._rows()
        for r in rows:
            if r['stratum'] in ('S4', 'S5'):
                fam = int(r['family_id'].split('fam')[1])
                r['h_triggered'] = True
                r['h_success'] = fam < 2
                r['d_success'] = False
        with tempfile.TemporaryDirectory() as td:
            g = stats.load_pairs(self._write(td, rows))
        c = stats.bootstrap(g, 'h', stats.IMPROVE, iterations=2000, seed=stats.SEED)
        n = stats.naive_case_level(g, 'h', stats.IMPROVE, iterations=2000, seed=stats.SEED)
        self.assertGreater(c['ci_upper_pp'] - c['ci_lower_pp'], n['ci_upper_pp'] - n['ci_lower_pp'])

    def test_bootstrap_reproducible_and_triggered_inconclusive_when_few(self):
        with tempfile.TemporaryDirectory() as td:
            g = stats.load_pairs(self._write(td, self._rows()))
        a = stats.bootstrap(g, 'h', stats.IMPROVE, iterations=200, seed=21)
        self.assertEqual(a, stats.bootstrap(g, 'h', stats.IMPROVE, iterations=200, seed=21))
        for s in stats.IMPROVE:
            for r in g[s]: r['h_triggered'] = False
        self.assertEqual(stats.triggered_bootstrap(g, iterations=100, seed=21)['status'], 'INCONCLUSIVE')

    def test_family_cells_report_negative_cells(self):
        rows = self._rows()
        for r in rows:
            if r['stratum'] == 'S4' and r['family_id'].endswith('fam0'):
                r['h_triggered'] = True; r['d_success'] = True; r['h_success'] = False
        with tempfile.TemporaryDirectory() as td:
            g = stats.load_pairs(self._write(td, rows))
        cells = stats.family_cells(g, 'h', stats.IMPROVE)
        self.assertGreater(cells['negative_fraction'], 0)
        self.assertEqual(cells['cell_count'], 12)

    # ----- H gate -----
    CATALOG = [{'tool': 'read_config', 'params': {'service': ['app-3', 'db-3']}},
               {'tool': 'read_logs', 'params': {'service': ['app-3', 'db-3'], 'window': ['last_5m', 'last_1h']}}]
    OBS = [{'id': 'obs_status', 'tool': 'service_status', 'available_at_step': 0,
            'payload': {'service': 'app-3', 'status': 'running', 'ready': False}}]

    def _proposal(self, **over):
        p = {'action': 'REQUEST_READ',
             'claims': [{'obs_id': 'obs_status', 'payload_path': 'ready', 'equals': False}],
             'next_tool': 'read_config', 'next_params': {'service': 'db-3'}}
        p.update(over)
        return p

    def _check(self, proposal, trigger='D_OBSERVATION_CONFLICT', obs=None, **kw):
        args = dict(step=0, allowed_tools={'read_config', 'read_logs'}, tool_catalog=self.CATALOG,
                    reads_used=0, read_budget=1)
        args.update(kw)
        return evidence.check_proposal(trigger, proposal, obs if obs is not None else self.OBS, **args)

    def test_h_gate_accepts_grounded_read_with_catalog_params(self):
        r = self._check(self._proposal())
        self.assertEqual(r['decision'], 'SUGGEST_READ_ONLY')
        self.assertTrue(r['grounded'])
        self.assertNotIn('claim_verified', r)
        self.assertEqual(self._check(self._proposal(), trigger='D_CLEAR')['decision'], 'KEEP_D')

    def test_h_gate_rejects_bad_claims(self):
        for change in ({'obs_id': 'obs_missing'}, {'equals': True}, {'payload_path': 'phantom'}):
            prop = self._proposal()
            prop['claims'][0].update(change)
            self.assertEqual(self._check(prop)['decision'], 'KEEP_D')
        future = json.loads(json.dumps(self.OBS)); future[0]['available_at_step'] = 2
        self.assertEqual(self._check(self._proposal(), obs=future)['decision'], 'KEEP_D')

    def test_h_gate_budget_parameters_duplicates(self):
        self.assertEqual(self._check(self._proposal(), reads_used=1)['reason'], 'READ_BUDGET_EXHAUSTED')
        self.assertEqual(self._check(self._proposal(next_params={'service': 'ghost'}))['reason'], 'PARAMETER_VALUE_NOT_IN_CATALOG')
        self.assertEqual(self._check(self._proposal(next_params={}))['reason'], 'INVALID_READ_PARAMETERS')
        self.assertEqual(self._check(self._proposal(next_params={'service': 'db-3', 'x': 'y'}))['reason'], 'INVALID_READ_PARAMETERS')
        key = evidence.read_key('read_config', {'service': 'db-3'})
        self.assertEqual(self._check(self._proposal(), already_read=[key])['reason'], 'DUPLICATE_READ')
        self.assertEqual(self._check(self._proposal(next_tool='service_status'))['reason'], 'NOT_AUTHORIZED_READ_TOOL')

    def test_h_gate_rejects_write_tool_and_model_flags(self):
        self.assertEqual(self._check(self._proposal(next_tool='delete_file'), allowed_tools={'delete_file'})['decision'], 'KEEP_D')
        forged = self._proposal(); forged['verified'] = True
        self.assertEqual(self._check(forged)['reason'], 'INVALID_PROPOSAL_SHAPE')
        missing = self._proposal(); del missing['next_params']
        self.assertEqual(self._check(missing)['reason'], 'INVALID_PROPOSAL_SHAPE')

    def _after_read(self, recheck, new_id='obs_db_cfg', reveal=None, pre=('obs_status',)):
        gate = self._check(self._proposal())
        trusted = json.loads(json.dumps(self.OBS)) + [{
            'id': 'obs_db_cfg', 'tool': 'read_config', 'available_at_step': 1, 'payload': {'max_connections': 5},
            'reveal_on': reveal or {'tool': 'read_config', 'params': {'service': 'db-3'}}}]
        return evidence.finalize_after_read(gate, recheck, trusted_observations=trusted,
                                            allowed_diagnoses={'db_limit'}, pre_read_observation_ids=set(pre),
                                            new_observation_id=new_id)

    def test_h_adopts_cause_only_if_d_proof_uses_the_new_observation(self):
        good = lambda _: {'status': 'VERIFIED_DIAGNOSIS', 'cause_id': 'db_limit', 'proof_observation_ids': ['obs_status', 'obs_db_cfg']}
        r = self._after_read(good)
        self.assertEqual(r['decision'], 'ADOPT_VERIFIED_D_RECHECK')
        self.assertTrue(r['d_verified'])
        no_new = lambda _: {'status': 'VERIFIED_DIAGNOSIS', 'cause_id': 'db_limit', 'proof_observation_ids': ['obs_status']}
        self.assertEqual(self._after_read(no_new)['reason'], 'D_PROOF_DOES_NOT_USE_NEW_OBSERVATION')
        abstain = lambda _: {'status': 'ABSTAIN', 'cause_id': None, 'proof_observation_ids': []}
        self.assertEqual(self._after_read(abstain)['reason'], 'NO_VERIFIED_CAUSAL_PROOF')
        made_up = lambda _: {'status': 'VERIFIED_DIAGNOSIS', 'cause_id': 'made_up', 'proof_observation_ids': ['obs_db_cfg']}
        self.assertEqual(self._after_read(made_up)['decision'], 'KEEP_D')

    def test_h_rejects_unrelated_or_preexisting_new_observation(self):
        good = lambda _: {'status': 'VERIFIED_DIAGNOSIS', 'cause_id': 'db_limit', 'proof_observation_ids': ['obs_db_cfg']}
        wrong_read = {'tool': 'read_config', 'params': {'service': 'app-3'}}
        self.assertEqual(self._after_read(good, reveal=wrong_read)['reason'], 'NEW_OBSERVATION_NOT_FROM_AUTHORIZED_READ')
        self.assertEqual(self._after_read(good, pre=('obs_status', 'obs_db_cfg'))['reason'], 'NEW_OBSERVATION_NOT_NEW_OR_UNKNOWN')
        self.assertEqual(self._after_read(good, new_id=None)['reason'], 'READ_REVEALED_NOTHING')

    # ----- fixture validity -----
    def test_selection_sensitivity_flags_insensitive_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            def rows(sensitive):
                out = []
                for st in ('S4', 'S5'):
                    for i in range(60):
                        k = i < sensitive
                        out.append({'case_id': f'{st}-{i}', 'family_id': 'f', 'stratum': st,
                                    'd_budgeted_success': not k, 'd_unbounded_success': True})
                return out
            p = Path(td)/'s.jsonl'
            p.write_text('\n'.join(json.dumps(x) for x in rows(10)))
            self.assertEqual(sens.evaluate(p)['status'], 'FIXTURE_SELECTION_INSENSITIVE')
            p.write_text('\n'.join(json.dumps(x) for x in rows(30)))
            self.assertEqual(sens.evaluate(p)['status'], 'FIXTURE_VALID')
            with self.assertRaises(ValueError): sens.evaluate(p, min_share=0.1)
            bad = rows(5); bad[0]['d_budgeted_success'] = True; bad[0]['d_unbounded_success'] = False
            p.write_text('\n'.join(json.dumps(x) for x in bad))
            with self.assertRaises(ValueError): sens.evaluate(p)


    # ----- forked D/H and COMPLETE sufficient proof -----
    def test_separate_branches_start_same_snapshot_and_budget(self):
        case = json.loads(DUMMY_S4.read_text())
        fork = branch.fork_fixture_case(case, lambda obs, req: 'D_OBSERVATION_CONFLICT')
        d, h = fork['d'], fork['h']
        self.assertEqual(d.snapshot_hash, h.snapshot_hash)
        self.assertEqual(d.public_state(), h.public_state())
        self.assertEqual(d.remaining, h.remaining)
        self.assertEqual(d.remaining, 1)
        self.assertNotIn('oracle', json.dumps(h.public_state()))
        self.assertNotIn('max_connections', json.dumps(h.public_state()))
        d.read('service_status', {'service': 'cache-3'})
        self.assertEqual(d.remaining, 0)
        self.assertEqual(h.remaining, 1)  # NEVER charged for D's reads
        self.assertNotIn('obs_cache_status', json.dumps(h.public_state()))
        revealed = h.read('read_config', {'service': 'db-3'})
        self.assertEqual([x['id'] for x in revealed], ['obs_db_cfg'])
        self.assertEqual(h.remaining, 0)
        self.assertIn('obs_db_cfg', json.dumps(h.public_state()))
        self.assertEqual(d.remaining, h.remaining)

    def test_fork_preflight_sees_no_oracle_or_hidden_evidence(self):
        case = json.loads(DUMMY_S4.read_text())
        def preflight(obs, user_request):
            self.assertEqual({o['id'] for o in obs}, {'obs_app_log_tail', 'obs_app_cfg'})
            self.assertNotIn('max_connections', json.dumps(obs))
            self.assertNotIn('oracle', json.dumps(obs))
            return 'D_ABSTAIN'
        fork = branch.fork_fixture_case(case, preflight)
        self.assertTrue(fork['b_allowed'])
        self.assertEqual(fork['d'].read_keys, ())
        fork2 = branch.fork_fixture_case(case, lambda obs, req: 'D_CLEAR')
        self.assertFalse(fork2['b_allowed'])
        self.assertIsNone(fork2['h'])  # no local model requested

    def test_each_branch_enforces_own_read_budget_and_catalog(self):
        case = json.loads(DUMMY_S4.read_text())
        d = branch.fork_fixture_case(case, lambda obs, req: 'D_ABSTAIN')['d']
        with self.assertRaisesRegex(ValueError, 'PARAMETER_NOT_IN_CATALOG'):
            d.read('read_config', {'service': 'unauthorized'})
        with self.assertRaisesRegex(ValueError, 'INVALID_READ'):
            d.read('delete_file', {'service': 'app-3'})
        self.assertEqual(d.remaining, 1)
        d.read('read_config', {'service': 'db-3'})
        with self.assertRaisesRegex(ValueError, 'READ_BUDGET_EXHAUSTED'):
            d.read('read_logs', {'service': 'app-3', 'window': 'last_1h'})

    def test_complete_proof_sets_are_required_not_individual_valid_ids(self):
        case = json.loads(DUMMY_S4.read_text())
        self.assertFalse(fixture.oracle_proof_satisfied(case, 'db_connection_limit_below_pool', ['obs_db_cfg'], visible_observation_ids={'obs_app_cfg','obs_db_cfg'}))
        self.assertFalse(fixture.oracle_proof_satisfied(case, 'db_connection_limit_below_pool', ['obs_db_cfg','obs_app_cfg'], visible_observation_ids={'obs_app_cfg'}))
        self.assertFalse(fixture.oracle_proof_satisfied(case, 'db_connection_limit_below_pool', ['obs_app_cfg'], visible_observation_ids={'obs_app_cfg','obs_db_cfg'}))
        self.assertTrue(fixture.oracle_proof_satisfied(case, 'db_connection_limit_below_pool', ['obs_db_cfg','obs_app_cfg'], visible_observation_ids={'obs_app_cfg','obs_db_cfg'}))
        self.assertFalse(fixture.oracle_proof_satisfied(case, 'wrong_cause', ['obs_db_cfg','obs_app_cfg'], visible_observation_ids={'obs_app_cfg','obs_db_cfg'}))

    def test_schema_rejects_hidden_required_proof_beyond_budget(self):
        with tempfile.TemporaryDirectory() as td:
            case = json.loads(DUMMY_S4.read_text())
            # Both required pieces hidden behind DIFFERENT reads, budget=1 -> impossible.
            app = next(x for x in case['observations'] if x['id']=='obs_app_cfg')
            app['reveal_on'] = {'tool':'read_config','params':{'service':'app-3'}}
            app['available_at_step'] = 1
            p = Path(td)/'bad.json'; p.write_text(json.dumps(case))
            with self.assertRaisesRegex(ValueError, 'SELECTION_UNSOLVABLE'):
                fixture.validate(SCHEMA,p)

    def test_alternative_complete_sets_allow_one_feasible_route(self):
        with tempfile.TemporaryDirectory() as td:
            case = json.loads(DUMMY_S4.read_text())
            case['oracle']['required_proof_sets'] = [['obs_db_cfg','obs_app_cfg'], ['obs_db_cfg','obs_cache_status']]
            # second alternative requires 2 distinct reads, but first is sufficient
            p=Path(td)/'good.json';p.write_text(json.dumps(case))
            self.assertTrue(fixture.validate(SCHEMA,p))
            self.assertTrue(fixture.oracle_proof_satisfied(case, 'db_connection_limit_below_pool', ['obs_db_cfg','obs_app_cfg'], visible_observation_ids={'obs_app_cfg','obs_db_cfg'}))
            self.assertFalse(fixture.oracle_proof_satisfied(case, 'db_connection_limit_below_pool', ['obs_db_cfg'], visible_observation_ids={'obs_app_cfg','obs_db_cfg'}))
        self.assertFalse(fixture.oracle_proof_satisfied(case, 'db_connection_limit_below_pool', ['obs_db_cfg','obs_app_cfg'], visible_observation_ids={'obs_app_cfg'}))

    def test_runtime_attribution_and_complete_evaluator_proof(self):
        case = json.loads(DUMMY_S4.read_text())
        forks = branch.fork_fixture_case(case, lambda obs, req: 'D_OBSERVATION_CONFLICT')
        h = forks['h']
        visible = h.public_state()['observations']
        pool = next(x for x in visible if x['id']=='obs_app_cfg')
        self.assertEqual(pool['payload']['pool_size'], 50)
        proposal = {'action':'REQUEST_READ', 'claims': [{'obs_id':'obs_app_cfg',
                     'payload_path':'pool_size', 'equals':50}],
                    'next_tool':'read_config','next_params':{'service':'db-3'}}
        result = evidence.check_proposal(forks['d_trigger'],proposal,visible,
                  step=0,allowed_tools={'read_config'},tool_catalog=case['tool_catalog'],
                  reads_used=h.reads_used,read_budget=case['read_budget'],already_read=h.read_keys)
        self.assertEqual(result['decision'],'SUGGEST_READ_ONLY')
        preids = [x['id'] for x in visible]
        new = h.read(result['next_tool'],result['next_params'])
        self.assertEqual(len(new),1)
        # Model never sees the oracle. D rule independently compares observed values.
        def recheck(observations):
            by_id = {o['id']:o['payload'] for o in observations}
            if by_id['obs_app_cfg']['pool_size'] > by_id['obs_db_cfg']['max_connections']:
                return {'status':'VERIFIED_DIAGNOSIS','cause_id':'db_connection_limit_below_pool',
                        'proof_observation_ids':['obs_app_cfg','obs_db_cfg']}
            return {'status':'ABSTAIN','cause_id':None,'proof_observation_ids':[]}
        runtime = evidence.finalize_after_read(result,recheck,
                    trusted_observations=h.host_observations(),
                    allowed_diagnoses={'db_connection_limit_below_pool'},
                    pre_read_observation_ids=preids,new_observation_id='obs_db_cfg')
        self.assertEqual(runtime['decision'],'ADOPT_VERIFIED_D_RECHECK')
        self.assertTrue(fixture.oracle_proof_satisfied(case,runtime['cause_id'],runtime['proof_observation_ids'], visible_observation_ids={o['id'] for o in h.public_state()['observations']}))
        self.assertFalse(fixture.oracle_proof_satisfied(case,runtime['cause_id'],['obs_db_cfg'], visible_observation_ids={'obs_app_cfg','obs_db_cfg'}))


if __name__ == '__main__':
    unittest.main()
