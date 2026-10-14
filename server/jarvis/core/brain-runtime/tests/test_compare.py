import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from compare_runs import diff

class Comparisons(unittest.TestCase):
    def test_success_gate_and_actual_tokens(self):
        a={'case-1':{'passed':True,'quality':.8,'api_input_tokens':300,'api_output_tokens':100}}
        b={'case-1':{'passed':True,'quality':.9,'api_input_tokens':200,'api_output_tokens':100}}
        output=diff(a,b)
        self.assertEqual(output['api_token_delta'],-100)
        self.assertTrue(output['quality_gate_pass'])
    def test_reject_quality_regression_despite_lower_tokens(self):
        a={'x':{'passed':True,'quality':.9}}
        b={'x':{'passed':False,'quality':.5}}
        result=diff(a,b)
        self.assertFalse(result['quality_gate_pass'])
        self.assertIsNone(result['api_token_delta'])
    def test_missing_quality_means_unmeasured_not_success(self):
        a={'same':{'passed':True,'quality':None}}
        b={'same':{'passed':True,'quality':None}}
        result=diff(a,b)
        self.assertIsNone(result['quality_gate_pass'])
        self.assertIn('undecided',result['decision'])

    def test_reject_incomparable_cases(self):
        with self.assertRaises(ValueError):diff({'x':{'passed':True}}, {'y':{'passed':True}})
