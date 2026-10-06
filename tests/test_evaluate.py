import csv
import json
import math
import tempfile
import unittest
from pathlib import Path
from evaluate import auc, metrics, bootstrap, read_predictions, evaluate


def rows(labels, scores):
    return [dict(sample_id=str(i), group_id=str(i//2), split='test', condition='fixture',
                 label=y,score=s) for i,(y,s) in enumerate(zip(labels,scores))]


class EvaluationTests(unittest.TestCase):
    def test_perfect_auc(self):
        self.assertEqual(auc(rows([0,1,0,1],[.1,.8,.2,.9])),1)

    def test_reversed_auc(self):
        self.assertEqual(auc(rows([0,1,0,1],[.9,.2,.8,.1])),0)

    def test_tied_auc(self):
        self.assertEqual(auc(rows([0,1,0,1],[.5,.5,.5,.5])),.5)
        self.assertEqual(auc(rows([0,1,0,1],[.1,.5,.5,.9])),.875)

    def test_confusion_and_threshold_boundary(self):
        m=metrics(rows([0,1,0,1],[.5,.5,.2,.1]),.5, comparison='>=')
        self.assertEqual([m[k] for k in ['tp','fp','tn','fn']],[1,1,1,1])
        self.assertEqual(m['f1'],.5)

    def test_undefined_precision(self):
        self.assertIsNone(metrics(rows([0,1],[.1,.1]),.5)['precision'])
        self.assertIsNone(auc(rows([0,0],[.1,.8])))

    def test_cluster_bootstrap_reproducibility(self):
        r=rows([0,1]*8,[.1,.9]*8)
        a=bootstrap(r,.5,100,7)
        self.assertEqual(a,bootstrap(r,.5,100,7))
        self.assertEqual(a['auroc']['interval'],[1,1])

    def check_bad_csv(self, r, match):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'p.csv'
            with p.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(r[0]));w.writeheader();w.writerows(r)
            with self.assertRaisesRegex(ValueError,match): read_predictions(p)

    def test_duplicate_id(self):
        r=rows([0,1],[.1,.9]);r[1]['sample_id']=r[0]['sample_id']
        self.check_bad_csv(r,'Duplicate')

    def test_group_leakage(self):
        r=rows([0,1],[.1,.9]);r[1]['split']='validation'
        self.check_bad_csv(r,'leakage')

    def test_nonfinite_score(self):
        self.check_bad_csv(rows([0,1],[math.nan,.9]),'finite')

    def test_missing_score(self):
        self.check_bad_csv(rows([0,1],['',.9]),'empty')

    def test_out_of_range_score(self):
        self.check_bad_csv(rows([0,1],[-.1,.9]),'finite')

    def test_full_pipeline_and_metadata(self):
        root=Path(__file__).resolve().parents[1]
        r=evaluate(root/'examples/fixture_predictions.csv',root/'examples/fixture_metadata.json',.5,'software-validation',100)
        self.assertFalse(r['contains_detector_research_results'])
        self.assertEqual(r['conditions']['synthetic_fixture']['metrics']['n'],8)
        with self.assertRaisesRegex(ValueError,'purpose'):
            evaluate(root/'examples/fixture_predictions.csv',root/'examples/fixture_metadata.json',.5,'study',100)


if __name__=='__main__': unittest.main()
