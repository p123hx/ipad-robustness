import copy
import math
import unittest
from audit_corpus import pair_records
from design import binomial_upper, minimum_zero_error_n, paired_comparison
from evaluate import metrics, read_predictions
from pathlib import Path


class DesignTests(unittest.TestCase):
    def setUp(self):
        self.rows=read_predictions(Path(__file__).resolve().parents[1]/'examples/paired_counterexample.csv')

    def test_paper_strict_threshold(self):
        r=[dict(label=0,score=.54),dict(label=1,score=.54)]
        self.assertEqual(metrics(r,.54)['fp'],0)
        self.assertEqual(metrics(r,.54)['tp'],0)
        self.assertEqual(metrics(r,.54,'>=')['fp'],1)

    def test_exact_zero_and_all_error(self):
        self.assertAlmostEqual(binomial_upper(0,100),1-.05**.01,places=14)
        self.assertEqual(binomial_upper(100,100),1)
        self.assertAlmostEqual(binomial_upper(1,1),1)

    def test_sample_requirement_is_minimal(self):
        for target,n in [(.05,59),(.01,299),(.001,2995)]:
            self.assertEqual(minimum_zero_error_n(target),n)
            self.assertLessEqual(binomial_upper(0,n),target)
            self.assertGreater(binomial_upper(0,n-1),target)

    def test_invalid_binomial_input(self):
        for k,n in [(0,0),(2,1),(-1,2),(False,1)]:
            with self.assertRaises(ValueError):binomial_upper(k,n)

    def test_shared_controls_and_balanced_identity(self):
        result=paired_comparison(self.rows,'reference','shifted',.54,100,42)
        d=result['differences']
        self.assertEqual(d['false_positive_rate']['interval'],[0,0])
        self.assertEqual(d['recall']['estimate'],-1)
        self.assertEqual(d['accuracy']['estimate'],d['recall']['estimate']/2)
        self.assertEqual(d['auroc']['estimate'],0)

    def test_pairing_is_order_independent_and_reproducible(self):
        a=paired_comparison(self.rows,'reference','shifted',.54,100,42)
        b=paired_comparison(list(reversed(self.rows)),'reference','shifted',.54,100,42)
        self.assertEqual(a,b)

    def test_missing_pair_rejected(self):
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            paired_comparison(self.rows[1:],'reference','shifted',.54,100)

    def test_changed_human_rejected(self):
        r=copy.deepcopy(self.rows);r[0]['score']+=.01
        with self.assertRaisesRegex(ValueError,'mismatch'):
            paired_comparison(r,'reference','shifted',.54,100)

    def test_repeated_human_rejected(self):
        r=copy.deepcopy(self.rows);r[4]['text_id']=r[0]['text_id'];r[6]['text_id']=r[0]['text_id']
        with self.assertRaisesRegex(ValueError,'reused'):
            paired_comparison(r,'reference','shifted',.54,100)

    def test_prompt_join_handles_row_permutation(self):
        a=[{'expected_output':x,'input':'AI '+x} for x in ['one','two']]
        h=[{'output':x,'input':'human '+x} for x in ['two','one']]
        paired=pair_records(a,h)
        self.assertTrue(all(x[1][1]['expected_output']==x[2][1]['output'] for x in paired))
        self.assertEqual(paired[0][1][0],0);self.assertEqual(paired[0][2][0],1)

    def test_ambiguous_and_missing_prompts_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):
            pair_records([{'expected_output':'a','input':'x'}]*2,[])
        with self.assertRaisesRegex(ValueError,'differ'):
            pair_records([{'expected_output':'a','input':'x'}],[{'output':'b','input':'y'}])


if __name__=='__main__':unittest.main()
