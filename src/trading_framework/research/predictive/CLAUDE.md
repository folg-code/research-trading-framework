# Predictive Research

Responsibility: declared learning-problem specs, labelled feature-matrix
construction, and purged walk-forward fold assignment. No estimators.

## Conventions specific to this module

- Domain imports are polars, numpy, and framework contracts only.
- To reuse `compute_forward_outcomes_for_horizons`, synthesize occurrence rows
  with `direction="long"` as a string. Do not import `signal_model`.
- Feature values come from an already-built `AnalysisFrame`. Do not call
  `run_analysis` from this package.
- `RANK` is rejected at matrix-build time in this slice: expanding versus
  cross-sectional rank is ambiguous, and a global rank would leak.
- Fold assignment is long format: one copy of each participating labelled row
  per fold, with `fold_id` and `fold_role`.
- `test_span` and `embargo_span` are applied as datetime arithmetic on
  `available_at`, not as a 1-minute bar count. Consecutive test windows are
  separated by `embargo_span` so expanding later folds cannot train on the
  gap after an earlier test.

## Tests

Unit tests live under `tests/unit/research/predictive/`. Architecture boundary
tests in `tests/unit/test_architecture_boundaries.py` also cover this package.
