"""Statistical design utilities for matched generator comparisons.

These routines consume scores, not text or model weights. Exact binomial
bounds require independent Bernoulli observations and a fixed decision rule.
"""
import math
import random
from collections import defaultdict


def binomial_cdf(k, n, p):
    if k < 0:
        return 0.0
    if k >= n or p == 0:
        return 1.0
    if p == 1:
        return 0.0
    terms = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
             + i * math.log(p) + (n-i) * math.log1p(-p) for i in range(k+1)]
    largest = max(terms)
    return min(1.0, math.exp(largest) * math.fsum(math.exp(t-largest) for t in terms))


def binomial_upper(k, n, confidence=0.95):
    """One-sided Clopper-Pearson upper bound, including k=0 and k=n."""
    if type(k) is not int or type(n) is not int or n <= 0 or not 0 <= k <= n:
        raise ValueError('Require integer counts 0 <= k <= n and n > 0')
    if not 0 < confidence < 1:
        raise ValueError('Confidence must be in (0,1)')
    if k == n:
        return 1.0
    alpha = 1-confidence
    if k == 0:
        return -math.expm1(math.log(alpha)/n)
    lo, hi = 0.0, 1.0
    for _ in range(64):
        mid = (lo+hi)/2
        if binomial_cdf(k, n, mid) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo+hi)/2


def minimum_zero_error_n(target, confidence=0.95):
    """Minimum independent trials for an upper bound <= target, IF k=0."""
    if not 0 < target < 1 or not 0 < confidence < 1:
        raise ValueError('Target and confidence must be in (0,1)')
    return math.ceil(math.log1p(-confidence)/math.log1p(-target))


def matched_groups(rows, reference, shifted):
    """Validate the one-human/one-AI, two-condition design before resampling."""
    if reference == shifted:
        raise ValueError('Reference and shifted conditions must differ')
    groups = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        if row['split'] != 'test' or row['condition'] not in {reference, shifted}:
            continue
        cell = groups[row['group_id']][row['condition']]
        if row['label'] in cell:
            raise ValueError('Matched design requires one row per label/condition/group')
        if not row.get('text_id', '').strip():
            raise ValueError('Matched comparison requires text_id for shared-human checks')
        cell[row['label']] = row
    if len(groups) < 2:
        raise ValueError('Matched comparison requires at least two source groups')
    seen_humans = set()
    for g, cells in groups.items():
        if set(cells) != {reference, shifted} or any(set(c) != {0, 1} for c in cells.values()):
            raise ValueError(f'Incomplete matched group: {g}; no complete-case dropping')
        h0, h1 = cells[reference][0], cells[shifted][0]
        if h0['text_id'] != h1['text_id'] or h0['score'] != h1['score']:
            raise ValueError(f'Shared human text/score mismatch: {g}')
        if h0['text_id'] in seen_humans:
            raise ValueError('Human text reused across source groups')
        seen_humans.add(h0['text_id'])
    return groups


def paired_comparison(rows, reference, shifted, threshold, repetitions=2000,
                      seed=20261006, comparison='>'):
    from evaluate import metrics, quantile
    if repetitions < 100:
        raise ValueError('Use at least 100 bootstrap repetitions')
    groups = matched_groups(rows, reference, shifted)
    keys = sorted(groups)
    names = ('auroc', 'recall', 'accuracy', 'false_positive_rate')
    def difference(drawn):
        a = [groups[g][reference][y] for g in drawn for y in (0,1)]
        b = [groups[g][shifted][y] for g in drawn for y in (0,1)]
        ma, mb = metrics(a, threshold, comparison), metrics(b, threshold, comparison)
        return {k: mb[k]-ma[k] for k in names}
    point = difference(keys)
    rng = random.Random(seed)
    draws = {k: [] for k in names}
    for _ in range(repetitions):
        delta = difference(rng.choices(keys, k=len(keys)))
        for k in names:
            draws[k].append(delta[k])
    return {'contrast': 'shifted minus reference', 'reference': reference,
            'shifted': shifted, 'n_groups': len(keys), 'seed': seed,
            'repetitions': repetitions, 'method': 'paired source-group percentile bootstrap',
            'confidence': 0.95,
            'scope': 'conditional on fixed detector, threshold and collected generations',
            'differences': {k: {'estimate': point[k],
                'interval': [quantile(draws[k], .025), quantile(draws[k], .975)],
                'status': 'degenerate_resamples' if min(draws[k]) == max(draws[k]) else 'computed'}
                for k in names}}
