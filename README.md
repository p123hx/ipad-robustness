# IPAD robustness evaluation protocol

Working draft created 2026-10-03 at Hongxi Pu's direction.

**Status: protocol and score-evaluation software, not an empirical IPAD report.**
No IPAD model was run, no new text corpus was collected, and no detector
performance findings are reported. The fixture is invented numerical input for
software tests only. It must never be included as a research-results table.

## Contents

- `IPAD_Robustness_Protocol.pdf`: four-page preliminary research protocol.
- `evaluate.py`: Python 3.10+ standard-library evaluator for saved detector scores.
- `tests/test_evaluate.py`: regression tests for metrics and input validation.
- `examples/fixture_predictions.csv` and `fixture_metadata.json`: synthetic
  software-check inputs; not human/AI text or IPAD predictions.
- `validation/`: executed checks, clearly labeled as software validation.
- `study_metadata.template.json`: information to complete before real evaluation.
- `build_report.py`: PDF source; requires reportlab, not needed for evaluation.
- `SOURCE_AUDIT.txt`: source locations and reproduction issues to resolve.

## Run the software checks

```sh
python3 -m unittest discover -s tests -v
python3 evaluate.py --predictions examples/fixture_predictions.csv \
  --metadata examples/fixture_metadata.json --threshold 0.5 \
  --purpose software-validation --bootstrap 2000 \
  --out validation/fixture_metrics.json
```

The 0.5 threshold is a software example, NOT an IPAD reproduction setting.
Output timestamps vary; metric values are deterministic for a fixed input and seed.

## Real score input

CSV fields:

| Field | Meaning |
|---|---|
| sample_id | Unique row ID. Repeated texts in different conditions need distinct row IDs and the same source group. |
| group_id | Stable original prompt/source-document group; all human, generated and perturbed descendants stay in one split. |
| split | train, validation or test; only test rows enter reported performance. |
| condition | One evaluable human-versus-AI setting, e.g. reference_generator or shifted_generator. Include both labels in each condition. |
| label | 0 = human; 1 = AI-generated. Provenance must establish this independently of the detector. |
| score | Finite normalized score in [0,1]; larger means more likely AI-generated. |

Use the same group_id for matched reference/shifted conditions. Confidence
intervals are calculated separately within conditions; this version does NOT
compute confidence intervals for between-condition differences. Do not treat
overlap/non-overlap of separate intervals as a significance test. No pooled
overall metric is produced, to avoid double-counting reused human controls.

Complete `study_metadata.template.json` in a new file. Record the threshold
decision before inspecting target-test predictions. Supply expected_rows from
the full input manifest, before inference; do not adjust it to hide failures.
The evaluator rejects missing scores and count mismatches. It cannot discover
missing examples if the manifest/count itself is wrong. Identifier checks do
not replace textual deduplication or a training-contamination audit.

```sh
python3 evaluate.py --predictions real_predictions.csv \
  --metadata completed_study_metadata.json --threshold YOUR_FIXED_THRESHOLD \
  --purpose study --bootstrap 2000 --out real_results.json
```

Do not feed generated explanatory text, ROUGE scores or bare yes/no labels into
the probability column. This package does not implement IPAD inference. First
verify tokenization, normalized yes/no score extraction, adapter-to-module
mapping, regeneration, fusion, and threshold calibration. A substituted
generator, prompt or quantized checkpoint defines a modified configuration and
must be recorded as such.

## Completed and pending

Completed: protocol draft; public source inspection; CPU score evaluator;
unit checks and a separate numerical cross-check against scikit-learn.

Pending: researcher review; exact generator/domain/corpus selection; source and
license audit; end-to-end IPAD inference validation; real prediction collection;
empirical analysis. This repository publishes the protocol and software work in
progress on 2026-10-03. No Zenodo DOI has been assigned. No novelty, peer-review,
adoption or impact claim is made for this work.

The PDF is the pre-publication working-draft snapshot from earlier on the same
date; its pending-publication checklist records that earlier state. This README
records the current repository status.

AI assistance was used to draft the protocol and write/check the software.
Hongxi Pu should review and take responsibility for scientific choices and any
public authorship statement before release. No Meta data or code is included.

## Publication preparation

A first release can accurately be described as an *evaluation protocol and
software work in progress*, not a completed robustness study. Use the actual
release date. A timestamp records when that version was deposited; it does not
establish when the underlying ideas originated or validate their scientific merit.
Do not describe planned experiments as completed. The repository owner selected
the MIT License when creating this repository; see LICENSE. Third-party models
and datasets retain their own terms and are not redistributed here.

Before publishing, remove private data, review authorship, confirm citations,
replace draft metadata, and verify the commands above in a fresh checkout.
The `.gitignore` prevents default raw data, credentials and local caches from
being staged, but cannot replace a review of files selected for publication.

## Build the PDF

Install ReportLab and the DejaVu fonts. `build_report.py` currently expects
DejaVu TTF files under `/usr/share/fonts/truetype/dejavu/`; adjust FONT_ROOT for
your operating system, then run `python3 build_report.py`.
