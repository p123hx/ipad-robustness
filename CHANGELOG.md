# Changes

## 0.2 — 2026-10-06

- Audited 500 public IPAD/OUTFOX source groups against immutable releases.
  Prompt-based joining recovers all pairs; 492 align at the same row position.
  Cross-checked human/reference passages and recovered original generation contexts.
- Added a deterministic hash manifest with 100 development, 300 test and 100
  reserve groups. This is a new analysis split of existing public test data.
- Added paired bootstrap differences and shared-human consistency checks.
- Added exact one-sided false-positive-rate bounds and zero-error sample planning.
- Changed the evaluator's default boundary rule from `>=` to `>` to match
  the published IPAD rule. `--comparison '>='` retains the previous behavior.
- Added a constructed ranking-versus-threshold counterexample, numerical
  verification, and revised five-page protocol. No new IPAD inference results.

## 0.1 — 2026-10-03

Initial protocol and saved-score evaluator with synthetic software fixtures.
