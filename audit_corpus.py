"""Audit and pair two public IPAD/OUTFOX files. No model inference.

Downloads are opt-in. Raw passages stay in the local cache; outputs contain
only hashes, row numbers and counts. Exact file hashes pin the audited input.
"""
import argparse
import csv
import hashlib
import io
import json
import pickle
import urllib.request
from pathlib import Path

REVISION = 'e57952ab8f36a77421a02f96ac2a2fa13d324b6e'
FILES = {
    'test_outfox.csv': 'cf3449ab676c089872929e47e8139d3a7da5ea8435a2158d679701eb19de7932',
    'test_human_outfox.jsonl': '171bd27949071086b3a04338eec74b5aa1e31241748d7314e914bae895e4572e',
}
OUTFOX_REVISION = '8dd6bfdec8e24ff6aeecae3015ab663f257e0350'
OUTFOX_FILES = {
    'data/common/test/test_contexts.pkl': 'd515fc54874e620f42cf2d5d24cffb9258c2c87db48895e90d49686481ed7a13',
    'data/common/test/test_humans.pkl': '62c6e3ec8c7c1519b51573ac18bc3504957015c2326ad5137faaed33f098ea64',
    'data/common/test/test_problem_statements.pkl': '5f6cdf6e27611a8c7ee8b092f6490eeaa6f74557e08749604d95549f6944104d',
    'data/chatgpt/test/test_lms.pkl': '6e4d3d5abfaea3aae925cd5e2c178c1108bcf6e4682a166621d22ded4db47cb8',
}


class PrimitiveOnly(pickle.Unpickler):
    def find_class(self, module, name):
        raise ValueError('Loading pickle classes is prohibited')


def verify_outfox(cache, ai, human, download):
    arrays, sources = {}, []
    for name, expected in OUTFOX_FILES.items():
        path=cache/Path(name).name
        url=f'https://raw.githubusercontent.com/ryuryukke/OUTFOX/{OUTFOX_REVISION}/{name}'
        if not path.exists():
            if not download:
                raise ValueError(f'Missing {path}; use --download')
            with urllib.request.urlopen(url,timeout=60) as response:
                path.write_bytes(response.read())
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected:
            raise ValueError(f'OUTFOX source hash mismatch: {name}')
        value=PrimitiveOnly(io.BytesIO(raw)).load()
        if type(value) is not list or not all(type(x) is str for x in value):
            raise ValueError('Expected list of strings in pinned OUTFOX source')
        arrays[Path(name).stem]=value
        sources.append({'url':url,'sha256':expected,'bytes':len(raw)})
    q,h,a=(arrays[k] for k in ['test_problem_statements','test_humans','test_lms'])
    if not len(q)==len(h)==len(a) or len(set(q))!=len(q):
        raise ValueError('Invalid OUTFOX source correspondence')
    contexts=arrays['test_contexts']
    if len(contexts)!=len(q) or not all(prompt in context for prompt,context in zip(q,contexts)):
        raise ValueError('Generation contexts do not match source problem statements')
    originals=dict(zip(q,zip(h,a)))
    human_index={prompt_key(r['output']):r['input'] for r in human}
    checks={'human_exact_matches':0,'reference_exact_matches':0,'reference_whitespace_normalized_matches':0}
    for row in ai:
        expected_h,expected_a=originals[row['expected_output']]
        checks['human_exact_matches']+=human_index[prompt_key(row['expected_output'])]==expected_h
        checks['reference_exact_matches']+=row['input']==expected_a
        checks['reference_whitespace_normalized_matches']+=prompt_key(row['input'])==prompt_key(expected_a)
    return {'sources':sources,'generation_context_prompt_matches':len(q),**checks},dict(zip(q,contexts))


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def prompt_key(text):
    return ' '.join(text.split())


def pair_records(ai_rows, human_rows):
    def index(rows, field):
        result = {}
        for i, row in enumerate(rows):
            key = prompt_key(row[field])
            if not key or key in result:
                raise ValueError('Empty or duplicate prompt; manual grouping required')
            if not row['input'].strip():
                raise ValueError('Empty passage')
            result[key] = (i, row)
        return result
    ai, human = index(ai_rows, 'expected_output'), index(human_rows, 'output')
    if ai.keys() != human.keys():
        raise ValueError('Prompt sets differ; no silent intersection is permitted')
    return [(k, ai[k], human[k]) for k in sorted(ai)]


def audit(cache, out, download=False):
    cache, out = Path(cache), Path(out)
    cache.mkdir(parents=True, exist_ok=True)
    sources = []
    for name, expected in FILES.items():
        url = f'https://huggingface.co/bellafc/IPAD/resolve/{REVISION}/testing_data/{name}'
        path = cache/name
        if not path.exists():
            if not download:
                raise ValueError(f'Missing {path}; use --download to fetch public source')
            with urllib.request.urlopen(url, timeout=60) as response:
                path.write_bytes(response.read())
        raw = path.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected:
            raise ValueError(f'Source hash mismatch: {name}')
        sources.append({'name': name, 'url': url, 'sha256': actual, 'bytes': len(raw)})
    ai = list(csv.DictReader(io.StringIO((cache/'test_outfox.csv').read_text(encoding='utf-8-sig'))))
    human = [json.loads(s) for s in (cache/'test_human_outfox.jsonl').read_text().splitlines() if s.strip()]
    paired = pair_records(ai, human)
    upstream, generation_contexts = verify_outfox(cache, ai, human, download)
    # Ordering uses a fixed salted hash; no detector score is consulted.
    paired.sort(key=lambda r: digest('ipad-followup-20261006\n'+r[0]))
    manifest = []
    for rank, (key, (ai_index, a), (human_index, h)) in enumerate(paired):
        split = 'development' if rank < 100 else 'test' if rank < 400 else 'reserve'
        manifest.append({'group_id': digest(key), 'split': split,
            'ai_file_row_1based': ai_index+1, 'human_file_row_1based': human_index+1,
            'prompt_sha256': digest(key), 'human_text_sha256': digest(h['input']),
            'generation_context_sha256': digest(generation_contexts[a['expected_output']]),
            'reference_text_sha256': digest(a['input']),
            'human_words': len(h['input'].split()), 'reference_words': len(a['input'].split())})
    summary = {'analysis_date': '2026-10-06', 'kind': 'public corpus structure audit',
        'contains_detector_performance_results': False, 'sources': sources,
        'ai_file_rows': len(ai), 'human_file_rows': len(human), 'matched_prompts': len(paired),
        'outfox_source_crosscheck': upstream,
        'positional_prompt_matches': sum(prompt_key(a['expected_output']) == prompt_key(h['output'])
                                         for a,h in zip(ai,human)),
        'unique_human_texts': len({r['human_text_sha256'] for r in manifest}),
        'unique_reference_texts': len({r['reference_text_sha256'] for r in manifest}),
        'cross_label_exact_text_overlap': len({r['human_text_sha256'] for r in manifest}
                                            & {r['reference_text_sha256'] for r in manifest}),
        'split_groups': {s: sum(r['split']==s for r in manifest) for s in ['development','test','reserve']},
        'pairing': 'unique prompt equality after whitespace normalization; case retained',
        'selection': 'lexicographic SHA256(salt + normalized prompt), salt ipad-followup-20261006\\n',
        'limitations': ['Exact matching does not establish near-duplicate independence.',
            'Prompt correspondence does not independently authenticate human authorship.',
            'This follow-up split does not establish exclusion from original training or evaluation.',
            'The released predicted_output field is not interpreted as a detector score.']}
    out.mkdir(parents=True, exist_ok=True)
    with (out/'source_groups.csv').open('w', newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(manifest[0]));writer.writeheader();writer.writerows(manifest)
    summary['manifest_sha256']=hashlib.sha256((out/'source_groups.csv').read_bytes()).hexdigest()
    (out/'corpus_audit.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache', default='data/raw/ipad_outfox')
    p.add_argument('--out', default='analysis')
    p.add_argument('--download', action='store_true')
    a=p.parse_args()
    print(json.dumps(audit(a.cache,a.out,a.download),indent=2))
