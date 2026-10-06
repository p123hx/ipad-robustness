#!/usr/bin/env python3
"""Evaluate saved binary detector scores. No inference, training or API calls.

Python >=3.10, standard library only. Label 1 means AI-generated; higher scores
must mean more likely AI-generated. A threshold is always supplied explicitly.
"""
import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

FIELDS = {'sample_id', 'group_id', 'split', 'condition', 'label', 'score'}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_predictions(path):
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if not FIELDS.issubset(reader.fieldnames or []):
            raise ValueError('Missing CSV fields: ' + ', '.join(sorted(FIELDS - set(reader.fieldnames or []))))
        rows = list(reader)
    if not rows:
        raise ValueError('Empty prediction file')
    seen, group_splits = set(), {}
    for line, row in enumerate(rows, 2):
        if any(not isinstance(row.get(k), str) or not row[k].strip() for k in FIELDS):
            raise ValueError(f'Line {line}: empty required field; failed inference must be resolved, not dropped')
        if row['sample_id'] in seen:
            raise ValueError(f'Duplicate sample_id: {row["sample_id"]}')
        seen.add(row['sample_id'])
        if row['split'] not in {'train', 'validation', 'test'}:
            raise ValueError(f'Line {line}: split must be train, validation or test')
        g = row['group_id']
        if g in group_splits and group_splits[g] != row['split']:
            raise ValueError(f'Group leakage across splits: {g}')
        group_splits[g] = row['split']
        if row['label'] not in {'0', '1'}:
            raise ValueError(f'Line {line}: label must be 0 or 1')
        row['label'] = int(row['label'])
        row['score'] = float(row['score'])
        if not math.isfinite(row['score']) or not 0 <= row['score'] <= 1:
            raise ValueError(f'Line {line}: score must be finite and in [0,1]')
    return rows


def auc(rows):
    """Mann-Whitney AUROC with average ranks for ties; undefined -> None."""
    ordered = sorted(rows, key=lambda r: r['score'])
    n_pos = sum(r['label'] for r in ordered)
    n_neg = len(ordered) - n_pos
    if not n_pos or not n_neg:
        return None
    rank_sum, i = 0.0, 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j]['score'] == ordered[i]['score']:
            j += 1
        average_rank = (i + 1 + j) / 2
        rank_sum += average_rank * sum(r['label'] for r in ordered[i:j])
        i = j
    return (rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def metrics(rows, threshold, comparison='>'):
    if comparison not in {'>', '>='}:
        raise ValueError('Comparison must be > or >=')
    if not rows:
        raise ValueError('No rows to score')
    tp = fp = tn = fn = 0
    for r in rows:
        pred = r['score'] > threshold if comparison == '>' else r['score'] >= threshold
        if pred and r['label']: tp += 1
        elif pred: fp += 1
        elif r['label']: fn += 1
        else: tn += 1
    div = lambda x, y: x / y if y else None
    return dict(n=len(rows), n_ai=tp+fn, n_human=tn+fp, tp=tp, fp=fp, tn=tn, fn=fn,
                accuracy=(tp+tn)/len(rows), precision=div(tp,tp+fp),
                recall=div(tp,tp+fn), f1=div(2*tp,2*tp+fp+fn),
                false_positive_rate=div(fp,fp+tn), auroc=auc(rows))


def quantile(values, p):
    values = sorted(values)
    x = (len(values)-1)*p
    lo, hi = math.floor(x), math.ceil(x)
    return values[lo] + (values[hi]-values[lo])*(x-lo)


def bootstrap(rows, threshold, repetitions=2000, seed=20261003, comparison='>'):
    """Percentile intervals resampling source groups, preserving paired rows."""
    groups = defaultdict(list)
    for r in rows: groups[r['group_id']].append(r)
    keys = sorted(groups)
    if len(keys) < 2:
        return {'status': 'insufficient_groups', 'n_groups': len(keys)}
    rng = random.Random(seed)
    names = ['accuracy', 'precision', 'recall', 'f1', 'false_positive_rate', 'auroc']
    samples = {k: [] for k in names}
    for _ in range(repetitions):
        drawn = [row for key in rng.choices(keys, k=len(keys)) for row in groups[key]]
        m = metrics(drawn, threshold, comparison)
        for k in names:
            if m[k] is not None: samples[k].append(m[k])
    result = {'method': 'source-group percentile bootstrap', 'confidence': 0.95,
              'n_groups': len(keys), 'repetitions': repetitions, 'seed': seed}
    for k, v in samples.items():
        reliable_count = len(v) >= max(20, math.ceil(0.8*repetitions))
        result[k] = {'valid_replicates':len(v), 'undefined_replicates':repetitions-len(v),
                     'interval': [quantile(v,.025),quantile(v,.975)] if reliable_count else None,
                     'status': ('degenerate_resamples' if min(v)==max(v) else 'computed') if reliable_count else 'too_few_defined_replicates'}
    return result


def evaluate(path, metadata_path, threshold, purpose, repetitions=2000, seed=20261003,
             comparison='>', paired_conditions=None):
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError('Threshold must be finite and in [0,1]')
    if repetitions < 100:
        raise ValueError('Use at least 100 bootstrap repetitions')
    meta = json.loads(Path(metadata_path).read_text())
    if meta.get('purpose') != purpose:
        raise ValueError('Metadata purpose does not match requested purpose')
    if meta.get('score_direction') != 'higher_is_ai':
        raise ValueError('Specify higher_is_ai score direction explicitly')
    if not isinstance(meta.get('expected_rows'), int):
        raise ValueError('Provide expected_rows before evaluating; audit coverage separately')
    if purpose == 'study':
        required = ['detector_id','detector_revision','dataset_revision','score_definition',
                    'threshold_basis','run_date','inference_configuration','source_manifest_sha256']
        for k in required:
            v = meta.get(k)
            if not isinstance(v,str) or not v.strip() or 'TODO' in v.upper() or '[' in v:
                raise ValueError(f'Complete study metadata field: {k}')
        if meta.get('inference_completed') is not True:
            raise ValueError('Study scoring requires completed real inference')
    rows = read_predictions(path)
    if len(rows) != meta['expected_rows']:
        raise ValueError('Row count differs from predeclared expected_rows; do not silently omit failures')
    conditions = defaultdict(list)
    for row in rows:
        if row['split'] == 'test': conditions[row['condition']].append(row)
    if not conditions:
        raise ValueError('No held-out test rows')
    output = {'purpose':purpose, 'contains_detector_research_results':purpose=='study',
              'created_utc':datetime.now(timezone.utc).isoformat(),
              'prediction_file_sha256':sha256(path), 'metadata_file_sha256':sha256(metadata_path),
              'evaluator_sha256':sha256(__file__), 'threshold':threshold,
              'decision_rule':f'score {comparison} threshold predicts AI', 'metadata':meta, 'conditions':{}}
    for i,(name,subset) in enumerate(sorted(conditions.items())):
        if {r['label'] for r in subset} != {0,1}:
            raise ValueError(f'Condition {name} must contain human and AI examples')
        output['conditions'][name] = {'metrics':metrics(subset,threshold,comparison),
                    'uncertainty':bootstrap(subset,threshold,repetitions,seed+i,comparison)}
    if paired_conditions:
        from design import paired_comparison, binomial_upper
        output['paired_comparison'] = paired_comparison(
            rows, *paired_conditions, threshold, repetitions, seed, comparison)
        ref_metrics = output['conditions'][paired_conditions[0]]['metrics']
        output['shared_human_fpr'] = {
            'false_positives': ref_metrics['fp'], 'n_unique_humans': ref_metrics['n_human'],
            'one_sided_95pct_upper': binomial_upper(ref_metrics['fp'], ref_metrics['n_human']),
            'assumption': 'independent human source groups, representative sampling and fixed threshold',
            'method': 'exact binomial upper bound; shared humans counted once'}
    return output


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--predictions',required=True)
    ap.add_argument('--metadata',required=True)
    ap.add_argument('--threshold',type=float,required=True)
    ap.add_argument('--purpose',choices=['software-validation','study'],required=True)
    ap.add_argument('--bootstrap',type=int,default=2000)
    ap.add_argument('--seed',type=int,default=20261003)
    ap.add_argument('--out',required=True)
    ap.add_argument('--comparison',choices=['>','>='],default='>')
    ap.add_argument('--paired',nargs=2,metavar=('REFERENCE','SHIFTED'))
    args=ap.parse_args()
    try:
        result=evaluate(args.predictions,args.metadata,args.threshold,args.purpose,args.bootstrap,args.seed,args.comparison,args.paired)
    except (ValueError,KeyError,OSError) as e:
        ap.error(str(e))
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(f'Saved {args.purpose} output to {args.out}')


if __name__ == '__main__': main()
