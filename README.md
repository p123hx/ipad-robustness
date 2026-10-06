# Evaluating IPAD under generator shift

A matched-source evaluation protocol, corpus audit and statistical implementation.

**Version 0.2 · 6 October 2026 · Hongxi Pu**

[Read the five-page protocol](IPAD_Robustness_Protocol.pdf).
The completed work is a public-data correspondence audit and statistical design
analysis. IPAD inference and the new-generator experiment remain to be run.

## What this version adds

- Joins 500 human/reference pairs from the public IPAD test files by problem
  statement. Only 492 pairs align by file position, so row-number pairing is
  insufficient. All human passages match the original OUTFOX release; all
  reference passages match after whitespace normalization.
- Recovers all 500 original generation contexts, including their length
  instructions, and records their hashes for subsequent generation.
- Creates a deterministic 100/300/100 development/test/reserve manifest with
  source identifiers and hashes. This is a split of existing public test data,
  not a newly collected corpus or proof of exclusion from IPAD training.
- Computes paired changes in recall, AUROC and accuracy while keeping human
  controls fixed. Missing pairs and inconsistent human scores are rejected.
- Quantifies the limits of a small human control set: zero errors among 100
  independent human texts gives a one-sided 95% FPR upper bound of 2.951%.
  At least 299 zero-error observations are needed for this bound to be <=1%.
- Includes a constructed score example in which AUROC stays at 1 while recall
  at a fixed threshold drops. These are not measured IPAD scores.

## Reproduce the completed analyses

Python 3.10+ is sufficient for the audit and evaluator. Run from this directory.
The download step fetches six pinned public source files (about 6.5 MB total).
Raw third-party passages stay in the ignored local cache; only hashes and counts
are committed. Pickled OUTFOX lists are hash-checked and loaded by an unpickler
that disallows class loading.

```sh
python3 audit_corpus.py --download
python3 design_analysis.py
python3 -m unittest discover -s tests -v
python3 evaluate.py --predictions examples/paired_counterexample.csv \
  --metadata examples/paired_counterexample_metadata.json \
  --threshold 0.54 --comparison '>' --purpose software-validation \
  --paired reference shifted --bootstrap 2000 --seed 20261006 \
  --out validation/paired_counterexample_metrics.json
```

The 500-row manifest and corpus findings are in `analysis/source_groups.csv`
and `analysis/corpus_audit.json`. Exact planning calculations are in
`analysis/design_calculations.json`. Files under `examples/` and `validation/`
contain constructed software inputs and validation outputs, not detector results.

For independent numerical checks and PDF generation:

```sh
python3 -m pip install -r requirements-validation.txt
python3 validate_numerics.py
python3 build_report.py
```

PDF generation uses DejaVu fonts under `/usr/share/fonts/truetype/dejavu/`.
Validation compares metrics against scikit-learn (200 randomized cases), exact
binomial bounds against SciPy (30 cases), and paired intervals against a separate
NumPy/scikit-learn calculation using the same 400 group draws. These checks
validate the implementation; they do not validate IPAD's detection performance.

## Real prediction interface

| CSV field | Meaning |
|---|---|
| sample_id | Unique evaluation row identifier. |
| text_id | Stable identifier/hash for the exact passage; required in paired mode. Shared human text has the same identifier in both conditions. |
| group_id | Original source group; all descendants remain in one split. |
| split | train, validation or test. Only test rows are evaluated. |
| condition | Reference or shifted generator condition. |
| label | 0 = human; 1 = AI, determined from source provenance. |
| score | Finite score in [0,1], with larger values indicating AI. |

The matched mode requires one human and one AI row in each condition per source
group. It checks shared human identifiers and scores, repeated human identifiers,
and complete group correspondence. It resamples a group simultaneously across
conditions, then computes shifted-minus-reference metric differences. Reused
human controls are counted once for the FPR upper bound. Zero-width bootstrap
intervals are flagged and must not be interpreted as absence of population risk.
Exact binomial bounds additionally assume independent representative human
samples and a fixed decision rule; identifiers alone do not establish independence.

Complete `study_metadata.template.json` with the actual inference provenance and
predeclared row count before invoking study mode. The wrapper validates declared
metadata and row counts; it cannot authenticate the declarations, detect every
near duplicate or establish training-set independence. Log every attempted
sample and resolve failures before scoring; never repair a count mismatch by
silently reducing the expected sample count.

```sh
python3 evaluate.py --predictions real_predictions.csv \
  --metadata completed_study_metadata.json --threshold 0.54 --comparison '>' \
  --purpose study --paired reference shifted --bootstrap 2000 \
  --seed 20261006 --out real_results.json
```

The published IPAD merge uses weight 0.45 for PTCV, 0.55 for RC, and a strict
`score > 0.54` decision rule. This package consumes saved continuous scores and
**does not implement IPAD inference**. Verify actual checkpoint semantics,
yes/no probability extraction, fusion and regeneration before using those
settings. The paper's component mapping, rather than a directory name alone,
should determine the score definition. Any replacement regeneration model or
quantization change must be documented as a configuration change.

## Interpretation and next experiment

The next experiment adds a generator using the recovered OUTFOX contexts.
No additional generator has yet been selected or tested. Freeze its version,
system message, decoding settings and the complete detector configuration before
collecting test scores. The historical reference and a new generation may differ
in more than model identity if the original sampling or system settings cannot
be recovered. A model-only comparison requires regenerating both conditions
under common documented settings.

The 300 test groups will yield 900 distinct passages and 1,200 condition-specific
rows: 300 human scores are reused, not independently observed twice. Report
recall and AUROC differences, shared-human FPR, coverage and component diagnostics.
The 20 qualitative examples are selected by manifest order before inference;
plausible reconstructed prompts are not, by themselves, evidence of faithfulness.

## Sources and versions

- Chen et al., IPAD, NeurIPS 2025: https://doi.org/10.52202/085713-5580
- IPAD public resources: https://huggingface.co/bellafc/IPAD
- OUTFOX: https://github.com/ryuryukke/OUTFOX
- Exact binomial bounds: https://itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbino.htm

Immutable source revisions and file digests are recorded in the corpus audit.
The [earlier protocol record on Zenodo](https://zenodo.org/records/23120967)
predates this revision; it should not be treated as archiving version 0.2 until a
new version containing these files is deposited. See [CHANGELOG.md](CHANGELOG.md).

AI tools assisted with drafting and software development. Source data and models
retain their original terms; the repository's license covers its own code.
