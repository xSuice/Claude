"""Security regressions: acceptance is evidence for files, not council compliance."""
import json
import unittest
import distiller

class EvidenceBoundary(unittest.TestCase):
    def test_unverified_council_constraints_are_not_claimed_as_complied(self):
        job = {'id':'j20261028-abcdef','revision':1,'verdict':'done','spec':{'data_class':'internal'}}
        plan = {'task_type':'doc.text','steps':[{'id':'s1','title':'Write report'}]}
        acceptance = {'ok':True,'deliverables':[{'ok':True}]}
        council = {'council':'SECURITY','constraints':['Verify encrypted backup before modifying production']}
        candidates = distiller.extract(job, plan, acceptance, [], council)
        decision = next(c for c in candidates if c['kind']=='decision')
        self.assertNotIn('in der Ausführung eingehalten', decision['body'])
        self.assertIn('nicht separat verifiziert', decision['body'])

    def test_candidates_redact_recognizable_secrets_before_storage(self):
        marker = 'ghp_' + 'X' * 36  # synthetic canary, not a credential
        job = {'id':'j20261028-abcdef','verdict':'done','fix_rounds':1,'spec':{'data_class':'private'}}
        plan = {'task_type':'doc.text','steps':[{'id':'s1','title':marker}]}
        candidates = distiller.extract(job, plan, {'ok':True,'deliverables':[{'ok':True}]},
            [{'id':1,'kind':'step_failed','text':marker}], {'council':'DEV','constraints':[marker]})
        self.assertTrue(candidates)
        self.assertNotIn(marker, json.dumps(candidates))

    def test_existing_candidate_is_redacted_again_when_written(self):
        import tempfile
        from pathlib import Path
        marker = 'ghp_' + 'Y' * 36
        cand = {'id':3,'title':marker,'kind':'procedure','body':marker,
                'evidence':{'job':'j20261028-abcdef','revision':1,'events':[], 'acceptance':{'ok':True}}, 'private':True}
        with tempfile.TemporaryDirectory() as tmp:
            path = distiller.write_note(Path(tmp), cand, 'portal:andrew')
            self.assertNotIn(marker, path.read_text())
            self.assertNotIn(marker.lower(), path.name.lower())

if __name__ == '__main__':
    unittest.main()
