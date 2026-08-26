# Predictive Research

Responsibility: declared learning-problem specs, labelled feature-matrix
construction, and purged walk-forward fold assignment. No estimators.

## Conventions specific to this module

- Domain imports are polars, numpy, and framework contracts only.
- To reuse `compute_forward_outcomes_for_horizons`, synthesize occurrence rows
  with `direction="long"` as a string. Do not import `signal_model`.
- Feature values come from an already-built `AnalysisFrame`. Do not call
  `run_analysis` from this package.
- Matrix `available_at` must not be later than `detected_at` (ADR-0023 §4 /
  SPRINT_039 §9.1). Look-ahead availability is rejected at build time. This is
  not `MarketBar.available_at`, which may be after `observed_at` and is not
  passed through to the labelled matrix.
- `RANK` is rejected at matrix-build time in this slice: expanding versus
  cross-sectional rank is ambiguous, and a global rank would leak.
- Fold assignment is long format: one copy of each participating labelled row
  per fold, with `fold_id` and `fold_role`.
- `test_span` and `embargo_span` are applied as datetime arithmetic on
  `available_at`, not as a 1-minute bar count. Consecutive test windows are
  separated by `embargo_span` so expanding later folds cannot train on the
  gap after an earlier test.
- Role assignment prefers embargo over purge when both apply (this fold's
  embargo, then a prior fold's embargo, then purge). A row in fold *n*'s
  embargo whose `label_end_at` also reaches fold *n+1*'s TEST stays
  `EMBARGOED` so later reports can count each guard (D-S039-09).

## Tests

Unit tests live under `tests/unit/research/predictive/`. Architecture boundary
tests in `tests/unit/test_architecture_boundaries.py` also cover this package.
