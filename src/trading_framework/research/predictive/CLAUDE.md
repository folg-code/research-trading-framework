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
- Importance (`importance.py`) is library-free permutation on TEST rows or
  TEST windows (`n_repeats=5`, `EstimatorSpec.seed`). Native gain/split comes
  from tree adapters only; sklearn and neural families return `None`. Train vs
  TEST primary-metric gap is stored as added `fold_primary` keys on
  `metrics.json`.
- Leaderboard (`leaderboard.py`) ranks runs that share one dataset fingerprint
  by pooled primary metric. S040 metric-layer baselines appear as rows; they
  are not estimator families. Neural families (`torch.*`) rank as ordinary
  estimator rows. Mismatched fingerprints are `PredictiveSpecError`.
- Learning curves (`learning_curves.py`) persist inner-train / inner-validation
  loss per outer fold plus the restored stopping epoch. Application writes
  `learning_curves.json` when `describe().resolved_params` carries those keys;
  missing sidecar skips the report panel.
- Sequence windows (`windows.py`) are library-free. `SequenceWindowSpec` is
  lookback + stride + `DROP` padding. Application builds windows **after** fold
  assignment on the full fold frame (all roles) and **before** `fit()` /
  `predict()` for sequence families. A window ending on `TEST` may contain only
  `TEST` rows; cross-role / cross-entity / gapped windows are dropped, never
  padded or truncated. Accounting is a sidecar JSON, not a predictions column.
  Sequence runs write `window_accounting.json`; missing sidecar skips the
  report panel. `research/predictive/` still must not import torch.
- Rank-2 permutation shuffles TEST columns. Rank-3 permutation shuffles one
  feature channel across windows with the same permutation on axis 0 so
  lookback structure is preserved. Do not flatten the last bar.
- `test_span` and `embargo_span` are applied as datetime arithmetic on
  `available_at`, not as a 1-minute bar count. Consecutive test windows are
  separated by `embargo_span` so expanding later folds cannot train on the
  gap after an earlier test.
- Role assignment prefers embargo over purge when both apply (this fold's
  embargo, then a prior fold's embargo, then purge). A row in fold *n*'s
  embargo whose `label_end_at` also reaches fold *n+1*'s TEST stays
  `EMBARGOED` so later reports can count each guard (D-S039-09).

- `promotion/` (Sprint 049, ADR-0029) is the pure-NumPy promoted-artifact
  evaluator: `PromotedArtifactParameters` (the parameter-file payload schema),
  `load_promoted_artifact` (the load-time format/family guard, no bypass), and
  `FittedNumpyPreprocessor` / `fit_numpy_preprocessor` (moved here from
  `infrastructure/ml/torch/preprocessing.py`, Q8/D-S049-08 — the torch adapter
  imports them downward from here now). This subpackage must not import
  `research.datasets` (layering runs `research/predictive` -> `research/datasets`,
  never the reverse — ADR-0029 §9); `load_promoted_artifact` accepts a
  structural `PromotedManifestLike` Protocol instead of the concrete
  `PromotedArtifactManifest` class for that reason. Practical reference (schema,
  store layout, both guards, the family restriction, the two parity
  comparisons): `docs/reference/PREDICTIVE_PROMOTION.md`. A promoted artifact
  is not a tradeable verdict and this package ships no Market Analysis
  component — see that document §1 and §9.

## Tests

Unit tests live under `tests/unit/research/predictive/`. Architecture boundary
tests in `tests/unit/test_architecture_boundaries.py` also cover this package.
