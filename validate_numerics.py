"""Independent numerical oracles: scikit-learn, SciPy and NumPy.

Executed validation concerns statistical code, not detector accuracy.
"""
import json
import random
from pathlib import Path
import numpy as np
import scipy
from scipy.stats import beta
import sklearn
from sklearn.metrics import roc_auc_score, accuracy_score, f1_score
from design import binomial_upper, paired_comparison
from evaluate import metrics


def main():
    rng=np.random.default_rng(20261006)
    metric_errors=[]
    for _ in range(200):
        y=np.array([0,1]+rng.integers(0,2,98).tolist())
        score=np.round(rng.random(100),2)
        threshold=float(rng.choice(score))
        actual=metrics([dict(label=int(a),score=float(b)) for a,b in zip(y,score)],threshold)
        pred=score>threshold
        oracle={'auroc':roc_auc_score(y,score),'accuracy':accuracy_score(y,pred),
                'f1':f1_score(y,pred,zero_division=0)}
        metric_errors.extend(abs(actual[k]-v) for k,v in oracle.items())
    bound_errors=[]
    for n in [1,2,10,50,100,300,1000]:
        for k in sorted({0,1,n//2,n-1,n}):
            oracle=1.0 if k==n else float(beta.ppf(.95,k+1,n-k))
            bound_errors.append(abs(binomial_upper(k,n)-oracle))
    # A nondegenerate matched example checks resampling, not just zero-width cases.
    n=24;human=rng.random(n);a=rng.random(n);b=np.clip(a+rng.normal(0,.25,n),0,1)
    rows=[]
    for i in range(n):
        for cond,v in [('a',a[i]),('b',b[i])]:
            for label,s in [(0,human[i]),(1,v)]:
                rows.append(dict(group_id=f'{i:03}',sample_id=f'{cond}{i}{label}',
                    text_id=f'h{i}' if label==0 else f'{cond}{i}',split='test',condition=cond,label=label,score=float(s)))
    result=paired_comparison(rows,'a','b',.54,400,42)
    oracle_rng=random.Random(42);samples={k:[] for k in ['auroc','recall','accuracy','false_positive_rate']}
    for _ in range(400):
        ix=np.array(oracle_rng.choices(list(range(n)),k=n))
        labels=np.tile([0,1],n)
        sa=np.column_stack([human[ix],a[ix]]).ravel()
        sb=np.column_stack([human[ix],b[ix]]).ravel()
        samples['auroc'].append(roc_auc_score(labels,sb)-roc_auc_score(labels,sa))
        samples['recall'].append(np.mean(b[ix]>.54)-np.mean(a[ix]>.54))
        samples['accuracy'].append(accuracy_score(labels,sb>.54)-accuracy_score(labels,sa>.54))
        samples['false_positive_rate'].append(0.0)
    paired_error=max(float(np.max(np.abs(np.quantile(v,[.025,.975])-result['differences'][k]['interval'])))
                     for k,v in samples.items())
    assert max(metric_errors)<1e-12
    assert max(bound_errors)<1e-12
    assert paired_error<1e-12
    out={'kind':'independent numerical software validation','seed':20261006,
         'metric_cases':200,'metric_max_abs_error':max(metric_errors),
         'exact_bound_cases':len(bound_errors),'bound_max_abs_error':max(bound_errors),
         'paired_bootstrap_draws':400,'paired_interval_max_abs_error':paired_error,
         'versions':{'numpy':np.__version__,'scipy':scipy.__version__,'scikit_learn':sklearn.__version__}}
    (Path(__file__).resolve().parent/'validation/independent_crosscheck.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))


if __name__=='__main__':main()
