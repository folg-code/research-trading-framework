# Predictive Research

Responsibility: declared learning-problem specs, labelled feature-matrix
construction, purged walk-forward fold assignment, the ML-free estimator
protocol (`PredictiveEstimator`, `EstimatorSpec`, preprocessing spec), and
library-free predictive metrics (`metrics.py`).

## Conventions specific to this module

- Domain imports are polars, numpy, and framework contracts only. Never
  import scikit-learn, XGBoost, LightGBM, CatBoost, or torch — not at runtime
  and not under `TYPE_CHECKING`. Architecture tests walk every `Import` /
  `ImportFrom`. The protocol is structural (`typing.Protocol`); it does not
  subclass sklearn types.
- Estimator family adapters live in `infrastructure/ml/`. This package must
  not import `infrastructure.ml`.
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
- Metrics (`metrics.py`) use numpy/polars only — never `sklearn.metrics`.
  Finance-aware scores always read the carried `forward_return` column;
  classification must not substitute `y_true`. Reference baselines
  (`CONSTANT_MEAN`, `MAJORITY_CLASS`, `RANDOM_PERMUTATION`) are metric-layer
  comparators, not registry families. `RANDOM_PERMUTATION` shuffles TEST
  predictions inside each fold with `EstimatorSpec.seed`. Reports always
  include per-fold **and** pooled results.
- Preprocessing (`PreprocessingSpec`) is fitted per fold on TRAIN rows only.
  `PURGED` and `EMBARGOED` never reach `fit()`. Default steps are
  `IMPUTE_MEDIAN` then `STANDARDIZE`. The sklearn Pipeline implementation is
  in the adapter, not here.
- Bounded candidate selection (`selection.py`) is library-free. `CandidateSetSpec`
  is declared and capped (default 8, hard max 16). Inner validation is the
  chronological suffix of outer TRAIN rows; outer TEST is predicted once after
  refit. Early-stopping eval roles may be TRAIN only.
- Importance (`importance.py`) is library-free permutation on TEST rows
  (`n_repeats=5`, `EstimatorSpec.seed`). Native gain/split comes from tree
  adapters only; sklearn returns `None`. Train vs TEST primary-metric gap is
  stored as added `fold_primary` keys on `metrics.json`.
- Leaderboard (`leaderboard.py`) ranks runs that share one dataset fingerprint
  by pooled primary metric. S040 metric-layer baselines appear as rows; they
  are not estimator families. Mismatched fingerprints are `PredictiveSpecError`.
- Sequence windows (`windows.py`) are library-free. `SequenceWindowSpec` is
  lookback + stride + `DROP` padding. The builder runs **after** fold
  assignment on the full fold frame (all roles). A window ending on `TEST`
  may contain only `TEST` rows; cross-role / cross-entity / gapped windows
  are dropped, never padded or truncated. Accounting is a sidecar JSON, not
  a predictions column. `research/predictive/` still must not import torch.
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
