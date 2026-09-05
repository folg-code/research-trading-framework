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
  with `direction="long"` as a string. Do not import `signal_model`. This is
  the `every_bar` path only: `signal_occurrences` recomputes `forward_return`
  with the occurrence's own real direction, but that recomputation happens in
  `application/predictive_research/resolve_signal_occurrences.py` (S056-T004),
  never here.
- `build_labelled_feature_matrix`'s `LabelledFeatureMatrix.candidates` is the
  full-grid frame *before* the completeness filter (one row per bar, always
  long-direction, with a `features_finite` flag) — it exists so a sample
  resolver can attribute a dropped row to its exact reason and read
  `label_end_at` for one bar without re-deriving it from a filtered sequence
  (D-S056-05). `label_expr` (public, was `_label_expr`) is reused the same
  way: a resolver maps its own recomputed `forward_return` to `label` with
  the exact rule `every_bar` uses, never a second implementation of it.
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

- `sample.py` (Sprint 056, ADR-0031) declares `SampleSpec` / `SampleKind` /
  `PredictiveTask` as pure data — DECLARATION only, no row resolution. Two
  kinds are SHIPPED: `every_bar` (default) and `signal_occurrences` (declared
  by `signal_model_file` + `signal_model_id`, never a run id or persisted
  occurrence artifact). `strategy_trades` and `labelled_setups` are declared,
  refused, and owned by **16F**; `sessions_or_windows` and the remaining
  reserved `PredictiveTask` names are refused as **later, unassigned**.
  Reserved names are deliberately **not members** of `SampleKind` /
  `PredictiveTask` — they only exist in `_RESERVED_SAMPLE_KIND_OWNERS` /
  `_RESERVED_PREDICTIVE_TASK_OWNERS`, so a reserved value can never be
  represented in memory; refusal always raises a named error
  (`ReservedSampleKindError` / `ReservedPredictiveTaskError`), never
  `PredictiveSpecError` generically. `PredictiveStudySpec.to_dict()` **elides**
  `sample` when the kind is `every_bar` and `task` when it is
  `FORWARD_RETURN` — this is what keeps every existing spec's
  `definition_hash` unchanged; do not make this serialization unconditional
  without a fresh ADR (it would churn every persisted hash and manifest).
  Resolving `signal_occurrences` into real rows (`evaluate_models` ->
  `materialize_signal_occurrences` -> filter-late row selection) is
  `application/predictive_research/resolve_signal_occurrences.py`'s job
  (S056-T004), not this package's — `research/predictive/` accepts an
  already-resolved row selection and must gain no import of `signal_model`,
  `strategy`, or `application` to do it. That module is a deliberate,
  narrowly-scoped exception to the wave4 architecture test
  (`tests/unit/test_architecture_boundaries.py`): it alone may import
  `trading_framework.strategy` / `trading_framework.signal_model`, per
  ADR-0031 Decision 3; `research.simulation` and `execution` stay forbidden
  for it too, enforced by that test's own narrower predicate.
- `SampleProvenance` (S056-T003, ADR-0031 Decision 6, `sample.py`) is the
  manifest-persisted record of a resolved sample: kind, task,
  `universe_row_count`, `resolved_row_count`, and `drop_counts` (per-reason,
  must sum to `universe_row_count - resolved_row_count`). It is written for
  **both** sample kinds — an `every_bar` build records `universe_row_count ==
  resolved_row_count` and `drop_counts == {}` explicitly, so "the whole grid
  was used" is a read, not an inference (Finding 5). A `signal_occurrences`
  build's provenance means something different by design: `universe_row_count`
  is the resolved occurrence count (`candidate_rows`, asserted equal to
  `occurrences.height`, D-S056-08), `resolved_row_count` is how many became a
  labelled row, and `drop_counts` names each of the same three reasons
  `every_bar` already uses (`incomplete_horizon`, `insufficient_data`,
  `null_features`) — `build_predictive_dataset` requires
  `request.signal_model` when the sample kind is `signal_occurrences` and
  raises a named `PredictiveDatasetError` if it is missing (no on-disk loader
  for `signal_model_file` exists anywhere in the framework yet; the caller
  supplies the already-constructed `SignalModelDefinition` directly, the same
  seam `preloaded_bars`/`preloaded_view` already use). `SampleProvenance` never
  enters `compute_dataset_fingerprint`'s inputs (`research/datasets/predictive.py`
  — `PREDICTIVE_DATASET_SCHEMA_V2` is additive over v1: a v1 manifest still
  loads with `sample_provenance is None`; only v2 requires it, enforced at
  `PredictiveDatasetRepository.write`).

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
  comparisons): `docs/reference/modules/PREDICTIVE_PROMOTION.md`. A promoted artifact
  is not a tradeable verdict and this package ships no Market Analysis
  component — see that document §1 and §9.

## Tests

Unit tests live under `tests/unit/research/predictive/`. Architecture boundary
tests in `tests/unit/test_architecture_boundaries.py` also cover this package.
