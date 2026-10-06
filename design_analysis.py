"""Reproduce analytical design calculations and a score-only counterexample.

The counterexample is constructed, not an IPAD measurement. No API is called.
"""
import csv
import json
import math
from pathlib import Path
from design import binomial_upper, minimum_zero_error_n, paired_comparison
from evaluate import metrics


def main():
    root=Path(__file__).resolve().parent
    out=root/'analysis';out.mkdir(exist_ok=True)
    sample_sizes=[50,100,300,1000]
    bounds=[{'n_independent_humans':n,'false_positives':0,
             'one_sided_95pct_fpr_upper':binomial_upper(0,n),
             'probability_zero_errors_if_true_fpr_1pct':.99**n} for n in sample_sizes]
    requirements=[{'target_fpr':p,'min_n_if_zero_errors':minimum_zero_error_n(p)} for p in [.05,.01,.001]]
    # Exact finite example: rankings are preserved while all AI scores cross
    # the fixed decision threshold. Human controls and source groups are shared.
    rows=[]
    for i in range(100):
        human=.1+.2*i/99
        for condition,ai in [('reference',.7+.2*i/99),('shifted',.35+.15*i/99)]:
            for label,score in [(0,human),(1,ai)]:
                rows.append(dict(sample_id=f'{condition}-{i}-{label}',group_id=f'g{i:03}',
                    text_id=f'h{i:03}' if label==0 else f'{condition}-a{i:03}',
                    split='test',condition=condition,label=label,score=score))
    path=root/'examples/paired_counterexample.csv'
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    meta={'purpose':'software-validation','score_direction':'higher_is_ai','expected_rows':len(rows),
          'description':'Constructed numerical counterexample; no text, detector or generation experiment.'}
    (root/'examples/paired_counterexample_metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
    output={'analysis_date':'2026-10-06','kind':'analytical study design and constructed score example',
        'contains_detector_performance_results':False,'zero_error_bounds':bounds,
        'zero_error_sample_requirements':requirements,
        'threshold':.54,'comparison':'>',
        'constructed_example':{c:metrics([r for r in rows if r['condition']==c],.54) for c in ['reference','shifted']},
        'interpretation':'Perfect ranking need not imply useful recall at a frozen threshold.',
        'assumptions':'Binomial calculations require independent representative human samples and a fixed threshold.'}
    (out/'design_calculations.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))


if __name__=='__main__':main()
