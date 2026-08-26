# Sprint 042 — Wave 0 Decisions

Binding decisions for Tree-Based Predictive Models (Phase 10B). Date: 2026-08-26.
Inherited locks from S039 / S040 / ADR-0023 are restated, not reopened.
Maintainer go-ahead 2026-08-26 (`pracuj dalej` after S041 integration PR #325
opened with green CI). No new ADR — ADR-0024 remains reserved for IDEA-014.

Basis: `SPRINT_042.md`, `ROADMAP.md` §13A Phase 10B, ADR-0023 (ACCEPTED),
`S040_WAVE0_DECISIONS.md`, `S041_WAVE0_DECISIONS.md` (reserved panel ids).

S041 report v1 is implemented on `sprint/predictive-research-report` and waits
on integration PR #325. Waves 1–3 of this sprint do **not** require that merge.
Wave 4 report panels (T017–T019) rebase onto `main` after #325 lands.

---

## Inherited locks (do not reopen)

```text
research/predictive/ stays ML-free (no sklearn / xgboost / lightgbm / catboost / torch)
Adapters live in infrastructure/ml/<lib>/ behind PredictiveEstimator
Durable facts are predictions.parquet + metrics.json; blobs are opaque (TD-022)
No model registry (TD-021)
Synthetic fixtures only — no NQ as S042 acceptance
No signals / strategy / simulation / IDEA-014
Models do not trade
Phase 10 has no PASS/FAIL robustness verdict
SHAP is deferred (SPRINT_042.md §9)
```

---

## D-S042-01 — Problem statement

S040 baselines are the control group. This sprint adds the default tabular
learners — gradient-boosted trees — through the **unchanged** estimator
protocol, then makes comparison honest: bounded inner-fold selection, pinned
threads, out-of-sample permutation importance, and a study leaderboard on one
dataset fingerprint.

A tree that cannot beat ridge on the same folds is a statement about the
features, not a reason to add SHAP.

---

## D-S042-02 — Sprint branch and PR base

```text
Integration branch: sprint/predictive-tree-models   (cut from main @ S040)
Working branches:   feat/ | fix/ | docs/ | test/   (cloud: cursor/<slug>-c340)
PR base:            sprint/predictive-tree-models  (never main until sprint integration)
```

Working-branch PRs squash-merge into the sprint branch. When S042 is complete,
one integration PR goes `sprint/predictive-tree-models` → `main`.

After #325 merges, rebase `sprint/predictive-tree-models` onto `main` before
Wave 4 (report panels). Do not merge S041 report code into this sprint by hand.

---

## D-S042-03 — Sprint slice

**This sprint ships exactly:** extra `ml-trees`, three tree adapters, determinism
enforcement, `CandidateSetSpec` + inner-fold selection, native + permutation
importance, train/test metric gap, study leaderboard, report panels that
register on the S041 panel registry.

| Order | Slice | Why |
|-------|--------|-----|
| 1 | Wave 0 | Binding S042 locks before extras or adapters |
| 2 | Extra + XGBoost | First adapter proves extra, registry, determinism, CI job |
| 3 | LightGBM + CatBoost | Remaining families, same protocol |
| 4 | Bounded selection | Inner validation; outer TEST touched once |
| 5 | Importance + gap | Honest diagnostics, library-free permutation |
| 6 | Leaderboard | One dataset fingerprint, including S040 baselines |
| 7 | Report panels | After #325; reserved id `feature_importance` |
| 8 | Closure | Comparison study + extra-free import test + docs |

**Not this sprint:** networks, SHAP, GPU, unbounded search, ensembling,
cross-study leaderboards, IDEA-014, NQ as acceptance.

---

## D-S042-04 — Methodology boundary

Restate of ADR-0023 §1. **Locked:**

```text
no signals
no strategy/
no signal_model/
no simulation
no promotion to Market Analysis components (IDEA-014 → S044 / ADR-0024)
```

A trained tree is never a tradable signal inside Phase 10.

---

## D-S042-05 — Package layout

```text
research/predictive/estimators.py          unchanged protocol (optional importance method)
research/predictive/selection.py           CandidateSetSpec + inner split (no ML libs)
research/predictive/importance.py          permutation importance over the protocol
research/predictive/leaderboard.py         comparison rows keyed by dataset fingerprint
infrastructure/ml/registry.py              register tree families (lazy factories)
infrastructure/ml/trees/xgboost/           adapter + factories
infrastructure/ml/trees/lightgbm/
infrastructure/ml/trees/catboost/
application/predictive_research/           selection loop + leaderboard write
scripts/predictive_research/               compare_predictive_runs.py (Wave 4)
```

`research/predictive/` still imports **polars**, **numpy**, and framework
contracts only. Architecture tests already forbid xgboost / lightgbm / catboost
outside `infrastructure/ml/`. Do not weaken them.

Application resolves families only through `resolve_estimator`. It must not
import `xgboost`, `lightgbm`, `catboost`, or `infrastructure.ml.trees.*`.

---

## D-S042-06 — Extra `ml-trees`

Policy inherited (D-S039-06 / ADR-0023 §3). S042 implements it.

**Locked:**

```text
[project.optional-dependencies]
ml-trees = [
  "xgboost>=2.1,<4.0",
  "lightgbm>=4.5,<5.0",
  "catboost>=1.2,<2.0",
]
```

```text
Do not add these libraries to [dependency-groups] dev
Do not add them to extra `ml`
Extra `ml` stays sklearn-only
Default `uv sync --locked --dev` stays extra-free
```

Tree families reuse S040 fold-local sklearn preprocessing
(`IMPUTE_MEDIAN` then `STANDARDIZE`). Resolving a tree family therefore
requires **both** extras:

```text
uv sync --locked --extra ml --extra ml-trees --dev
```

Missing `ml` while requesting a tree family raises `PredictiveExtraError`
naming extra `ml` (preprocessing). Missing `ml-trees` while requesting a tree
family raises `PredictiveExtraError` naming extra `ml-trees`.

Exact pins are `uv lock` work in PR 2 (T002).

---

## D-S042-07 — Dedicated CI job and pytest marker

**Locked:** add one job to the **existing** `.github/workflows/ci.yml`. Do not
create a second workflow file.

```text
Job id:     ml_trees
Name:       ML trees extra tests
Install:    uv sync --locked --extra ml --extra ml-trees --dev
Run:        uv run pytest -m ml_trees -q
```

Standard jobs remain extra-free. The unit job additionally excludes the new
marker once it exists:

```text
uv run pytest tests/unit -m "not ml and not ml_trees" --cov=...
```

Do **not** put `-m "not ml_trees"` in global `addopts`.

Marker name is `ml_trees` (underscore — pytest-safe). Extra name stays
`ml-trees` (hyphen — already locked in ADR-0023). Register the marker in
`pyproject.toml` because `--strict-markers` is on.

Tree test modules also call `pytest.importorskip("xgboost")` (or the library
under test) at module level so local extra-free pytest **skips** instead of
failing at collection.

The `ml_trees` job lands in the same PR that first has a `@pytest.mark.ml_trees`
test (PR 2). Until that PR, do not add the job.

mypy: add `ignore_missing_imports` overrides for `xgboost`, `xgboost.*`,
`lightgbm`, `lightgbm.*`, `catboost`, `catboost.*`. Default quality job stays
extra-free.

Tree adapters use **lazy import**. Module-level files under
`infrastructure/ml/trees/` must not import the libraries at import time. The
first import happens inside the factory / `fit()` path; failure becomes
`PredictiveExtraError`.

---

## D-S042-08 — Family identifiers

Stable strings, hashed into run identity. Namespaced by adapter (D-S040-15).

```text
xgboost.regressor      TaskType.REGRESSION
xgboost.classifier     TaskType.CLASSIFICATION   (binary)
lightgbm.regressor     TaskType.REGRESSION
lightgbm.classifier    TaskType.CLASSIFICATION   (binary)
catboost.regressor     TaskType.REGRESSION
catboost.classifier    TaskType.CLASSIFICATION   (binary)
```

Unknown ids are `PredictiveSpecError` even when extra `ml-trees` is installed.
Task-type mismatch (regressor family + CLASSIFICATION spec) is
`PredictiveSpecError`. Multiclass / ternary targets are rejected, same as
`sklearn.logistic`.

Reference baselines remain **not** registry families.

---

## D-S042-09 — Determinism and thread policy

Tree libraries are deterministic only when configured to be. The adapter owns
that, not the caller.

**Locked:**

```text
EstimatorSpec.seed is required (already D-S040-16)
Adapter pins thread count = 1 on every library
Thread count is recorded in EstimatorDescription.resolved_params
tree_method / booster / task_type locked to CPU deterministic histograms
GPU / CUDA / OpenCL device options rejected at spec validation
Non-deterministic histogram / subsample-without-seed options rejected
Do not rely on process-wide OMP/MKL env vars for the determinism test
```

Library-specific locks:

```text
XGBoost     nthread=1; tree_method="hist"; device="cpu"
            reject: cuda / gpu_hist / gpu_predictor
LightGBM    num_threads=1; deterministic=True; force_row_wise=True
            reject: device_type=gpu; boosting_type other than gbdt
CatBoost    thread_count=1; task_type="CPU"
            reject: task_type=GPU
```

Hyperparameters that the adapter overwrites (`nthread`, `num_threads`,
`thread_count`, `random_state` / `random_seed`, `deterministic`) may appear in
the spec; the adapter still forces the locked values. The resolved params in
`describe()` are what was actually used.

T007: same spec + same fixture fitted twice → byte-identical `predict()`
output. Reproducibility outranks throughput.

---

## D-S042-10 — Allowed hyperparameters

Adapters accept a **bounded** hyperparameter set. Unknown keys are
`PredictiveSpecError` (typos must not silently drop).

Shared (all three families):

```text
n_estimators / iterations / num_boost_round     positive int
max_depth                                       positive int
learning_rate                                   (0, 1]
subsample / bagging_fraction                    (0, 1]
reg_lambda                                      >= 0
```

Family-specific extras (still JSON-stable scalars):

```text
XGBoost     colsample_bytree, min_child_weight, reg_alpha, gamma
LightGBM    feature_fraction, min_child_samples, num_leaves, min_split_gain
CatBoost    l2_leaf_reg, border_count, bootstrap_type
            bootstrap_type in {Bernoulli, Bayesian, MVS} only
```

Default fixture hyperparameters (tests, not production advice):

```text
n_estimators=50
max_depth=3
learning_rate=0.1
```

`early_stopping_rounds` is **not** a free hyperparameter on `EstimatorSpec`.
It is only applied by the bounded-selection loop (D-S042-11).

---

## D-S042-11 — Bounded candidate selection

New domain value object in `research/predictive/selection.py` (no ML imports):

```text
CandidateSetSpec
  candidates         tuple[EstimatorSpec, ...]    explicitly declared
  max_candidates     int                          hard cap, default 8, max 16
  selection_metric   str                          spearman_ic | roc_auc
  inner_validation_fraction   float               default 0.20, in (0, 0.5]
```

Validation:

```text
len(candidates) >= 1
len(candidates) <= max_candidates
max_candidates <= 16
every candidate has the same task_type
selection_metric matches task_type
  REGRESSION       → spearman_ic
  CLASSIFICATION   → roc_auc
candidates are unique by (family, canonical hyperparameters, seed)
```

Exceeding the cap is `PredictiveSpecError`, not silent truncation.

Selection procedure per **outer** fold (application, not domain libraries):

1. Take outer `TRAIN` rows only. PURGED / EMBARGOED never enter selection.
2. Split them chronologically: last `inner_validation_fraction` is inner
   validation, the prefix is inner train. Minimum 10 inner-train and 10
   inner-validation rows; otherwise `PredictiveSpecError`.
3. Fit every candidate on inner train, score `selection_metric` on inner
   validation. Early stopping, if the library supports it, uses **this**
   inner validation only.
4. Select the winner. Ties break by candidate declaration order (stable).
5. Refit the winner on the full outer `TRAIN` rows **without** early stopping.
6. Predict the outer `TEST` rows once.

The outer test fold is never used for selection, early stopping, or
preprocessing. A unit test constructs a spec that would pass an outer-test
reference into early stopping and asserts `PredictiveSpecError`.

A run **without** `CandidateSetSpec` (single `EstimatorSpec`) does not split
TRAIN and does not use early stopping. That path stays identical to S040.

Selection trace (persisted JSON next to the run, not inside predictions):

```text
per outer fold:
  candidate family + hyperparameter hash
  inner-validation score
  selected: bool
winner family + spec, recorded in the run manifest
```

Different folds may select different winners. That variation is a stability
signal, not a bug.

---

## D-S042-12 — Importance and overfitting gap

### Native importance

Optional method on `FittedPredictiveEstimator`:

```text
native_feature_importance() -> NativeFeatureImportance | None
```

`NativeFeatureImportance` is a frozen domain value object: feature names,
`gain` scores, optional `split` / weight scores. Sklearn adapters return
`None` (no S042 requirement to invent it). Tree adapters always return it
after `fit()`.

Native scores are training-fold statistics. They are stored and displayed
but are not the conclusion.

### Permutation importance

Computed in `research/predictive/importance.py` with numpy only, against the
protocol `predict()` / metric functions already in `research/predictive/metrics.py`.

```text
rows:            outer TEST only
n_repeats:       5
seed:            EstimatorSpec.seed
metric:          same primary as D-S042-11
```

Application orchestrates; domain does not import adapters.

### Train-versus-test gap

Every tree run reports the primary metric on outer TRAIN rows (in-sample) and
outer TEST rows (OOS) per fold. The gap is a quality-flag input for the report,
not a PASS/FAIL verdict. Threshold for a warning (Wave 4, on the existing
`PredictiveReportQualityRules` object once #325 is on main):

```text
max_train_test_gap    0.20     |train − test| on the primary metric
```

Wave 1–3 persist the two values in `metrics.json` even before the report panel
exists. Do not change the S040 metrics schema except by **adding** keys
(`train_primary`, `test_primary`, `primary_gap`). Existing keys stay stable.

---

## D-S042-13 — Leaderboard

Not a model registry (TD-021). A derived comparison artifact:

```text
compare_predictive_runs(run_dirs) -> PredictiveLeaderboard
```

Rules:

```text
every run shares the same dataset fingerprint
pooled primary metric is the ranking key (higher is better)
S040 baselines (CONSTANT_MEAN / MAJORITY_CLASS / RANDOM_PERMUTATION) appear
  as rows when present in metrics.json — they are not estimator families
output: leaderboard.json written next to the first run or to a caller path
```

Mismatched dataset fingerprints are `PredictiveSpecError`. Cross-study
comparison spanning different fingerprints is out of scope (S044).

---

## D-S042-14 — Report panels (Wave 4, after #325)

S041 reserved `feature_importance`. S042 registers three panels; it does not
edit the assembly function:

```text
feature_importance     native + permutation, side by side
leaderboard            families + S040 baselines, one fingerprint
selection_trace        per-fold winner + inner scores + train/test gap
```

`learning_curves` stays reserved for S043.

Until #325 merges, do not add these panels. Waves 1–3 persist the data they
will read.

---

## D-S042-15 — First study dataset

**Locked:** S042 tests use **synthetic fixtures only**. No NQ.

Reuse S040 known-signal and noise-label fixtures. Additional tree-specific
assertions:

1. Known-signal: each tree family recovers primary metric above
   `RANDOM_PERMUTATION` on the same folds as ridge.
2. Noise label: tree families land within the permutation-baseline spread
   (leakage tripwire — boosting must not invent structure).
3. Determinism: two fits, identical predictions.
4. Extra-free: importing `infrastructure.ml.registry` does not import
   xgboost / lightgbm / catboost.

Comparison study (T020) is the same synthetic fixture, not a live market.

---

## D-S042-16 — Artifact persistence

Restate of D-S040-17 / TD-022.

```text
Durable facts:     predictions.parquet + metrics.json + selection_trace.json
Fitted blobs:      models/fold_{n}.bin — opaque joblib (serialize_artifact)
Not portable across library upgrades
Reproduce by re-fitting from the manifest
analyze_predictive_run still must not joblib.load blobs
```

Permutation importance is computed at analyze/report time from predictions +
the fitted protocol object in-memory during the run, then persisted as a
table. It is not recomputed by reading blobs later.

---

## D-S042-17 — PR sequence

Locked from `SPRINT_042.md` §8.

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 1 | `docs/predictive-tree-models-planning` | T001 Wave 0 |
| 2 | `feat/predictive-xgboost-adapter` | T002–T003, T006–T007 extra + XGBoost + determinism + CI job |
| 3 | `feat/predictive-lightgbm-catboost-adapters` | T004–T005 |
| 4 | `feat/predictive-bounded-candidate-selection` | T008–T012 |
| 5 | `feat/predictive-importance-diagnostics` | T013–T015 |
| 6 | `feat/predictive-study-leaderboard` | T016 |
| 7 | `feat/predictive-report-tree-panels` | T017–T019 (after #325) |
| 8 | `docs/predictive-tree-models-closure` | T020–T022 |

Each PR targets `sprint/predictive-tree-models`.

---

## Wave 0 checklist status

- [x] Sprint branch `sprint/predictive-tree-models` cut from `main` (D-S042-02)
- [x] Slice: trees + bounded search + importance; no SHAP / GPU / networks (D-S042-03)
- [x] Extra `ml-trees` separate from `ml`; both required to resolve a tree family (D-S042-06)
- [x] CI job `ml_trees` + marker `ml_trees` (D-S042-07)
- [x] Family ids namespaced `xgboost.*` / `lightgbm.*` / `catboost.*` (D-S042-08)
- [x] Thread count = 1; GPU rejected; repeated-fit identity (D-S042-09)
- [x] Candidate cap 16; inner validation 20%; outer TEST once (D-S042-11)
- [x] Permutation importance OOS; native importance not trusted alone (D-S042-12)
- [x] Leaderboard is not a registry (D-S042-13)
- [x] Report panels gated on #325 (D-S042-14)
- [x] Synthetic fixtures only (D-S042-15)
- [x] PR sequence from SPRINT_042 §8 (D-S042-17)

Approved by: Project Maintainer (go-ahead `pracuj dalej`, 2026-08-26)
Approved date: 2026-08-26
