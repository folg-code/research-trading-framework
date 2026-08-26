# Predictive Research

Responsibility: declared learning-problem specs and labelled feature-matrix
construction. No estimators.

## Conventions specific to this module

- Domain imports are polars, numpy, and framework contracts only.
- To reuse `compute_forward_outcomes_for_horizons`, synthesize occurrence rows
  with `direction="long"` as a string. Do not import `signal_model`.
- Feature values come from an already-built `AnalysisFrame`. Do not call
  `run_analysis` from this package.
- `RANK` is rejected at matrix-build time in this slice: expanding versus
  cross-sectional rank is ambiguous, and a global rank would leak.

## Tests

Unit tests live under `tests/unit/research/predictive/`. Architecture boundary
tests in `tests/unit/test_architecture_boundaries.py` also cover this package.
