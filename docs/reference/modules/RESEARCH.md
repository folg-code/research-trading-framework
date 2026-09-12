# Research — implementation map

This page records the existing packages and entry points for research. Start with the [module map](../system/MODULE_MAP.md) for system-wide placement and follow the links below for contracts and workflows.

## Packages and entry points

Research workflows share analytical and model-evaluation foundations, but remain independent application workflows.

### Signal and Model Research

| Responsibility | Package |
|---|---|
| Workflow orchestration | `application/signal_research/` |
| Research definitions | `research/signal_research/` |
| Observations | `research/observations/` |
| Context facts | `research/context/` |
| Forward outcomes | `research/outcomes/` |
| Run artifacts | `research/datasets/` |
| Analytics | `research/analytics/` |
| Reporting | `research/reporting/signal_research/` |

Workflow:

```text
Published Dataset
  → model evaluation
  → research facts
  → persisted run
  → read-only analytics
  → report
```

---

### Strategy Research

| Responsibility | Package |
|---|---|
| Workflow orchestration | `application/strategy_research/` |
| Shared OHLCV + model-eval cache | `application/strategy_research/shared_evaluation.py` |
| Strategy contracts | `strategy/` |
| Simulation engine | `research/simulation/` (incl. `simulation/kernels/fixed_bars.py` -- the original `@njit` fixed-bars kernel, unchanged since Sprint 013, and `simulation/kernels/bracket.py` -- the Sprint 048 / ADR-0028 `@njit` bracket kernel dispatched for `PriceBracketExit` models, with its own result dataclass and per-trade-reason materializers; no reference/non-njit counterpart, see TD-028) |
| Run artifacts | `research/datasets/` |
| Analytics | `research/analytics/` |
| Reporting | strategy reporting packages |

Workflow:

```text
Market Model + Signal Model + Strategy Definition
  → strategy research workflow
  → (optional SharedStrategyEvaluationContext)
  → simulation
  → persisted trades and equity
  → read-only analytics
  → dashboard
```

Robustness parameter / walk-forward / stress cells that share market and signal definitions reuse
`SharedStrategyEvaluationCache` so OHLCV load and `evaluate_models` run once per unique pair.

---

### Robustness Research

| Responsibility | Package |
|---|---|
| Workflow orchestration | `application/robustness_research/` |
| Experiment contracts | `research/robustness/` |
| Experiment analytics | `research/robustness/analytics/` |
| Experiment reports | robustness reporting packages |

Workflow:

```text
Research Definition
  → experiment variants
  → repeated strategy research runs
  → persisted experiment artifacts
  → aggregate analysis
  → verdict and report
```

---

### Predictive Research

Phase 10A: dataset foundation (Sprint 039), baseline estimators (Sprint 040),
and offline HTML report (Sprint 041). Phase 10B (Sprint 042) adds tree families
(XGBoost, LightGBM, CatBoost), bounded inner-fold selection, permutation
importance, a single-study leaderboard, and three report panels. Phase 10C
(Sprint 043) adds extra `dl` (CPU PyTorch): feedforward MLP, LSTM/GRU sequence
families, fold-contained windows, and learning-curve / window-accounting
panels. This workflow states a learning problem, persists a fingerprinted
labelled matrix, trains declared estimators per fold, and reviews one run as
standalone HTML. It does **not** emit signals or import `strategy/` /
`signal_model/`. `research/predictive/` stays library-free (polars, numpy,
framework contracts). Report figures live in `research/reporting/predictive/`
(plotly; no sklearn). ML libraries live behind optional extras `ml` /
`ml-trees` / `dl` and `infrastructure/ml/` adapters.

| Responsibility | Package |
|---|---|
| Study spec, features, labels, matrix, splits | `research/predictive/` |
| Estimator protocol, `EstimatorSpec`, `TaskType` | `research/predictive/estimators.py` |
| Fold-local preprocessing spec | `research/predictive/preprocessing.py` |
| Statistical + finance-aware metrics | `research/predictive/metrics.py` |
| Bounded candidate selection (`CandidateSetSpec`) | `research/predictive/selection.py` |
| Native + permutation importance, train/test gap | `research/predictive/importance.py` |
| Single-study leaderboard | `research/predictive/leaderboard.py` |
| Inner-training learning curves | `research/predictive/learning_curves.py` |
| Sequence windows + dropped-window accounting | `research/predictive/windows.py` |
| Dataset envelope, fingerprint, repository | `research/datasets/predictive.py` |
| Run envelope, fingerprint, repository | `research/datasets/predictive_run.py` |
| Workflow orchestration (build, run, analyze, render) | `application/predictive_research/` |
| Read-only HTML report | `research/reporting/predictive/` |
| Family registry + sklearn / tree / torch adapters | `infrastructure/ml/` (`registry.py`, `sklearn/`, `trees/xgboost/`, `trees/lightgbm/`, `trees/catboost/`, `torch/`) |
| Thin CLIs | `scripts/predictive_research/` |
| Storage paths | `infrastructure/storage/paths.py` |
| Promoted-artifact manifest, fingerprint, content-addressed repository (Phase 14A, Sprint 049) | `research/datasets/promoted_artifact.py` |
| Pure-NumPy promoted-artifact evaluator, parameter payload schema, load-time guard (Phase 14A) | `research/predictive/promotion/` |
| Promoted-artifact blob read, extraction, promotion-time version guard (Phase 14A) | `infrastructure/ml/promotion.py` |
| `promote_predictive_run` workflow (Phase 14A) | `application/predictive_research/promote_predictive_run.py` |
| Operator surface (Phase 14A) | `trading-cli research promote` (`apps/cli/`), `scripts/predictive_research/promote_predictive_run.py` |

Workflow:

```text
Published DatasetRef + PredictiveStudySpec (YAML/JSON)
  → run_analysis (declared FeatureSpec columns only)
  → labelled matrix (one row per complete evaluation bar)
  → purged + embargoed walk-forward fold roles
  → PredictiveDatasetEnvelope (manifest + fingerprint)
  → EstimatorSpec (family + hyperparameters + seed)
      or CandidateSetSpec (declared, capped; inner TRAIN split, TEST once)
  → run_predictive_research (fit on TRAIN per fold, predict on TEST;
      sequence families: application builds windows before fit / predict)
  → PredictiveRunEnvelope (predictions, metrics, opaque blobs)
  → analyze_predictive_run (writes metrics.json from predictions; never deserializes model blobs)
  → render_predictive_research_report (offline HTML; optional importance/selection/leaderboard/learning_curves/window_accounting sidecars; never fits or loads model blobs)
```

Samples are **evaluation bars**, not `SignalOccurrence` rows. Labels reuse
`compute_forward_outcomes_for_horizons` on a synthetic long-only occurrence
table (one row per bar). `FeatureTransform.RANK` is rejected at matrix build
(cross-sectional vs expanding rank is ambiguous; a global rank would leak).
Supported transforms this slice: `NONE`, `LOG`, `DIFF`, `PCT_CHANGE`.

The dataset fingerprint hashes study spec (`definition_hash`) + `OutputRef`
lineage + `DatasetRef` + time range. It never hashes materialized frame bytes.
`dataset_id` is the first 16 hex characters of that fingerprint.

Persisted fold roles: `TRAIN` / `TEST` / `PURGED` / `EMBARGOED`. Purged and
embargoed rows are retained with a role label, not deleted. Preprocessing
(`IMPUTE_MEDIAN`, `STANDARDIZE`) is fitted inside each fold on `TRAIN` rows
only; `PURGED` and `EMBARGOED` never reach `fit()`.

Estimator families this slice (registry ids): extra `ml` — `sklearn.ridge`,
`sklearn.elastic_net`, `sklearn.logistic` (binary). Extra `ml-trees` —
`xgboost.regressor`, `xgboost.classifier` (binary), `lightgbm.regressor`,
`lightgbm.classifier` (binary), `catboost.regressor`, `catboost.classifier`
(binary). Extra `dl` — `torch.feedforward.regressor`,
`torch.feedforward.classifier` (binary), `torch.lstm.regressor`,
`torch.lstm.classifier` (binary), `torch.gru.regressor`,
`torch.gru.classifier` (binary). Unknown family ids raise
`PredictiveSpecError`. Missing extra raises `PredictiveExtraError` naming the
extra. Tree families also need extra `ml` for fold-local preprocessing.
Neural families do **not** require extra `ml`; sequence families consume
rank-3 windows built by application. Reference baselines (`CONSTANT_MEAN`,
`MAJORITY_CLASS`, `RANDOM_PERMUTATION`)
are metric-layer comparisons, not registry families. Metrics are reported per
fold and pooled.

Optional extras:
`ml = ["scikit-learn>=1.6,<2.0"]`,
`ml-trees = ["xgboost-cpu>=2.1,<4.0", "lightgbm>=4.5,<5.0", "catboost>=1.2,<2.0"]`,
and `dl = ["torch>=2.6,<2.10"]` (CPU index).
Not in the default `dev` group. Dedicated CI jobs `ml`, `ml_trees`, and `dl`.
Standard unit CI stays extra-free (`uv sync --locked --dev`,
`-m "not ml and not ml_trees and not torch"`).

Storage:

```text
<workspace>/research/predictive_research/datasets/{dataset_id}/
  manifest.json
  features.parquet
  folds.json
<workspace>/research/predictive_research/runs/{run_id}/
  manifest.json
  predictions.parquet
  metrics.json
  report.html            # offline Plotly; first figure embeds JS inline
  selection.json         # candidate scores per fold; absent on single-estimator runs
  importance.json        # native + permutation importance and train/test gap
  leaderboard.json       # optional; single-study comparison of run dirs
  learning_curves.json   # optional; inner-train / inner-val loss per fold
  window_accounting.json # optional; dropped windows and effective sample
  models/fold_{n}.bin    # opaque; reproduce by re-fitting, not deserializing
```

**Promoted artifacts** (Phase 14A, Sprint 049) live in a separate,
content-addressed store under
`<workspace>/research/predictive_research/promoted/{artifact_fingerprint}/` —
see `docs/reference/modules/PREDICTIVE_PROMOTION.md` §3 for the exact two-file
layout, which is documented there only (not repeated here).

CLIs:

```text
uv run python scripts/predictive_research/build_predictive_dataset.py --storage-root <workspace> --definition <spec.yaml>
uv run python scripts/predictive_research/run_predictive_research.py --storage-root <workspace> --dataset-id <id> --estimator <spec.yaml>
uv run python scripts/predictive_research/analyze_predictive_run.py --storage-root <workspace> --run-id <id>
uv run python scripts/predictive_research/render_predictive_report.py --storage-root <workspace> --run-id <id>
uv run python scripts/predictive_research/compare_predictive_runs.py --run-dir <run> [--run-dir <run> ...]
```

### Tests

```text
tests/unit/research/
tests/unit/research/predictive/
tests/unit/strategy/
tests/unit/application/signal_research/
tests/unit/application/strategy_research/
tests/unit/application/robustness_research/
tests/unit/research/reporting/predictive/
tests/unit/application/predictive_research/
tests/unit/infrastructure/ml/
tests/integration/research/
```

### Deep references

- `../workflows/RESEARCH_METHODOLOGIES.md`
- `SYSTEM_OVERVIEW.md`
- `../modules/PREDICTIVE_PROMOTION.md` — promoted-artifact schema, store layout, both
  guards, the family restriction, and the two parity comparisons (Phase 14A)
- research ADRs (Predictive Research: ADR-0023; promotion: ADR-0029)

---
