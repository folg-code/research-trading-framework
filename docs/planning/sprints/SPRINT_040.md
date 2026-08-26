# Sprint 040 — Baseline Regression and Classification (Phase 10A)

## Metadata

```text
Sprint: 040
Phase: Phase 10A — Predictive Research Foundation
Status: Approved
Planned Start: 2026-08-26
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_039 (PredictiveDatasetEnvelope, fold roles, ADR-0023)
Sprint Branch: sprint/predictive-baselines
Task branch convention: feat/ | fix/ | docs/ | test/
Wave 0 decisions: docs/planning/sprints/S040_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/planning/ROADMAP.md (§13A Phase 10)
  - docs/adr/ADR-0023 (Predictive Research boundary — S039)
  - docs/planning/sprints/SPRINT_039.md
  - docs/planning/sprints/S040_WAVE0_DECISIONS.md
```

---

## 0. Slice choice

Sprint 039 produced a dataset nobody has learned from yet. This sprint introduces the **estimator
seam** and the **measurement vocabulary**, using models simple enough that a surprising result means
a bug rather than a discovery.

Linear and logistic baselines are not a warm-up. They are the control group: every tree and every
network in later sprints is judged against them, and a gradient-boosted model that cannot beat ridge
regression on the same folds is telling you something about the features, not the estimator.

**Out of scope:** trees, networks, hyperparameter search, reports.

---

## 1. Sprint Goal

```text
PredictiveDatasetEnvelope (S039)
    ↓
EstimatorSpec (family + hyperparameters + seed)
    ↓
run_predictive_research
    ↓
per fold: fit preprocessing + estimator on TRAIN, predict on TEST
    ↓
out-of-sample predictions (one row per test sample)
    ↓
statistical metrics + finance-aware metrics, per fold and pooled
    ↓
PredictiveRunEnvelope persisted with full run identity
```

Success: a maintainer runs one command against a persisted dataset and gets out-of-sample
predictions plus per-fold metrics, reproducible bit-for-bit from the run manifest.

---

## 2. In scope

- [ ] Optional dependency extra `ml` = scikit-learn.
- [ ] `PredictiveEstimator` protocol in `research/predictive/estimators.py` (domain, library-free).
- [ ] `EstimatorSpec` — family identifier, hyperparameters, random seed.
- [ ] Preprocessing pipeline spec fitted **per training fold** (imputation, standardization).
- [ ] scikit-learn adapter in `infrastructure/ml/sklearn/`.
- [ ] Regression baselines: ridge, elastic net. Classification baselines: logistic regression.
- [ ] Naive reference baselines (see §5) — the honest floor every model must clear.
- [ ] `run_predictive_research` application workflow with per-fold execution.
- [ ] Metrics module: statistical + finance-aware, per fold and pooled.
- [ ] `PredictiveRunEnvelope` v1 + run identity fingerprint.
- [ ] CLIs: run, analyze.

## 3. Out of scope

- Tree-based estimators (→ S042) and neural estimators (→ S043).
- Hyperparameter search of any kind — hyperparameters are declared, not searched (→ S042).
- HTML reports and dashboards (→ S041, S044).
- Feature selection, class rebalancing, sample weighting.
- Model artifact portability guarantees (see §8).
- Any path from predictions to orders, signals or strategies.

---

## 4. Estimator seam

```text
research/predictive/estimators.py        PredictiveEstimator protocol, EstimatorSpec, TaskType
research/predictive/preprocessing.py     preprocessing spec (fit-on-train contract)
research/predictive/metrics.py           metric computation over predictions
research/datasets/predictive_run.py      PredictiveRunEnvelope + repository
infrastructure/ml/registry.py            family id -> lazy adapter factory
infrastructure/ml/sklearn/               adapter: spec -> sklearn estimator -> protocol
application/predictive_research/         run + analyze orchestration
```

Protocol shape:

```text
PredictiveEstimator
  fit(features, target, sample_metadata) -> FittedPredictiveEstimator
FittedPredictiveEstimator
  predict(features) -> array
  predict_proba(features) -> array | None      (classification only)
  describe() -> EstimatorDescription           (library, version, resolved params)
```

### Binding rules

```text
research/predictive/ still imports no ML library — only the adapter does
scikit-learn is an optional extra; importing the framework without it must keep working
The adapter is selected by family identifier through a registry, not by isinstance checks
Preprocessing is fitted inside the fold, on TRAIN rows only, and never reused across folds
Rows with fold_role PURGED or EMBARGOED are never passed to fit()
describe() output is persisted — an unrecorded hyperparameter breaks reproducibility
```

Missing-extra behaviour: requesting an `sklearn` family without the extra installed raises an
explicit framework error naming the extra, never an `ImportError` traceback.

---

## 5. Metrics

Two layers, both mandatory. Statistical metrics say whether the model fits; finance-aware metrics
say whether the fit is worth anything.

### Statistical

```text
Regression       RMSE, MAE, R², Spearman rank IC, Pearson IC
Classification   accuracy, balanced accuracy, ROC AUC, PR AUC, log loss, Brier score
```

### Finance-aware

```text
Mean forward_return per prediction decile (out-of-sample only)
Top-decile minus bottom-decile spread
Hit rate at the declared decision threshold
Coverage: share of test rows above threshold
Mean forward_return of selected rows vs all test rows (the "is this better than always in" check)
```

### Reference baselines

Every run also reports the same metrics for:

```text
CONSTANT_MEAN        predict the training-fold mean (regression)
MAJORITY_CLASS       predict the training-fold majority (classification)
RANDOM_PERMUTATION   shuffle predictions within the test fold, fixed seed
```

An AUC of 0.54 means nothing without knowing the permutation baseline scored 0.50 with a spread of
±0.03 across folds. These baselines make that comparison automatic rather than optional.

Metrics are reported **per fold and pooled**. Pooled-only reporting hides the case where one fold
carries the entire result — the failure mode this whole track exists to catch.

---

## 6. Storage and run identity

```text
<workspace>/research/predictive_research/
  runs/{run_id}/
    manifest.json          dataset fingerprint, estimator spec, preprocessing, seeds, versions
    predictions.parquet    entity_id, fold_id, y_true, y_pred, y_proba
    metrics.json           per-fold + pooled, including reference baselines
    models/fold_{n}.bin    fitted artifact (opaque, see §8)
```

Run identity hashes:

```text
dataset fingerprint (S039)
estimator spec (family + hyperparameters + seed)
preprocessing spec
library name + version of the adapter backend
framework version
```

Two runs sharing a `run_id` must produce identical predictions. A library upgrade changes the
fingerprint by design — it is a different experiment, not the same one re-run.

---

## 7. Task breakdown

### Wave 0 — Planning

| Task | Description | Status |
|------|-------------|--------|
| S040-T001 | Wave 0 decisions (extras policy, artifact policy, first study dataset) | DONE |

### Wave 1 — Estimator seam

| Task | Description | Status |
|------|-------------|--------|
| S040-T002 | `PredictiveEstimator` protocol + `EstimatorSpec` + `TaskType` | TODO |
| S040-T003 | Estimator family registry + explicit missing-extra error | TODO |
| S040-T004 | Preprocessing spec with fit-on-train contract | TODO |
| S040-T005 | Optional extra `ml` in `pyproject.toml` + docs | TODO |

### Wave 2 — scikit-learn adapter

| Task | Description | Status |
|------|-------------|--------|
| S040-T006 | Adapter package `infrastructure/ml/sklearn/` | TODO |
| S040-T007 | Ridge + elastic net regression families | TODO |
| S040-T008 | Logistic regression classification family | TODO |
| S040-T009 | `describe()` capturing library version and resolved parameters | TODO |

### Wave 3 — Run orchestration

| Task | Description | Status |
|------|-------------|--------|
| S040-T010 | `run_predictive_research` per-fold execution loop | TODO |
| S040-T011 | Prediction table assembly (test rows only) | TODO |
| S040-T012 | Model artifact persistence per fold | TODO |
| S040-T013 | `PredictiveRunEnvelope` + repository + run identity fingerprint | TODO |

### Wave 4 — Metrics

| Task | Description | Status |
|------|-------------|--------|
| S040-T014 | Regression metrics (RMSE, MAE, R², rank IC) | TODO |
| S040-T015 | Classification metrics (AUC, PR AUC, log loss, Brier, calibration bins) | TODO |
| S040-T016 | Finance-aware metrics (decile buckets, spread, hit rate, coverage) | TODO |
| S040-T017 | Reference baselines (constant, majority, permutation) | TODO |
| S040-T018 | Per-fold + pooled aggregation, `analyze_predictive_run` | TODO |

### Wave 5 — CLI, tests, closure

| Task | Description | Status |
|------|-------------|--------|
| S040-T019 | CLIs: `run_predictive_research.py`, `analyze_predictive_run.py` | TODO |
| S040-T020 | Determinism test: same spec → identical predictions | TODO |
| S040-T021 | Known-signal fixture test (see §9) | TODO |
| S040-T022 | Import test: framework usable without the `ml` extra | TODO |
| S040-T023 | Docs: MODULE_MAP, DATA_WORKFLOWS, RESEARCH_METHODOLOGIES, CURRENT_STATUS | TODO |

**Progress:** 1 / 23 tasks

---

## 8. Model artifact policy

The durable facts of a predictive run are **predictions and metrics**. Those are Parquet and JSON,
readable in ten years.

The fitted model is an opaque artifact tagged with library name and version, stored for convenience
(inspection, importance in S042). The framework makes **no promise** that it can be loaded after a
library upgrade, and no workflow may depend on reloading it — a run is reproduced by re-fitting from
the manifest, not by deserializing a blob.

This is recorded as accepted technical debt rather than solved with a model registry, which stays
deferred (IDEA-003 adjacent, `TECHNICAL_DEBT.md` §6).

---

## 9. Known-signal fixture test

A synthetic fixture where the label is a known function of one feature plus noise. The suite asserts:

1. Ridge recovers a positive rank IC well above the permutation baseline.
2. Logistic regression recovers AUC well above 0.5 on the binary variant.
3. On a fixture where the label is pure noise, all models land within the permutation baseline
   spread — no model may "find" structure that is not there.
4. Shuffling the label column destroys performance for every family.

Test 3 is the one that catches leakage introduced by future refactoring: if a noise dataset starts
scoring, something is passing information backwards.

---

## 10. Recommended PR sequence

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 1 | `docs/predictive-baselines-planning` | T001 Wave 0 |
| 2 | `feat/predictive-estimator-protocol` | T002–T005 seam + extra |
| 3 | `feat/predictive-sklearn-adapter` | T006–T009 adapter |
| 4 | `feat/predictive-run-orchestration` | T010–T013 run + envelope |
| 5 | `feat/predictive-metrics` | T014–T018 metrics + baselines |
| 6 | `feat/predictive-cli` | T019 CLIs |
| 7 | `test/predictive-determinism-and-signal` | T020–T022 test suite |
| 8 | `docs/predictive-baselines-closure` | T023 documentation |

Each PR targets `sprint/predictive-baselines`.

---

## 11. Acceptance criteria

1. One command trains baselines across all folds and persists predictions plus metrics.
2. `research/predictive/` still imports no ML library; boundary test enforces it.
3. The framework imports and all non-ML tests pass without the `ml` extra installed.
4. Requesting an unavailable family raises a framework error naming the missing extra.
5. Preprocessing statistics differ per fold, proven by a test asserting fold-local fitting.
6. `PURGED` and `EMBARGOED` rows never reach `fit()`.
7. Every run reports the three reference baselines alongside model metrics.
8. Metrics exist per fold and pooled; pooled-only output is rejected in review.
9. Re-running an unchanged spec yields identical predictions and an identical `run_id`.
10. Noise-label fixture produces no better-than-baseline result for any family.
11. CI green: `ruff check`, `ruff format --check`, `mypy`, `pytest`.

---

## 12. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Preprocessing fitted on the whole dataset | Fold-local fitting contract + explicit test |
| Metrics look good because one fold dominates | Per-fold reporting mandatory; pooled never stands alone |
| A weak signal is mistaken for an edge | Permutation and constant baselines reported on every run |
| scikit-learn leaks into domain imports | Boundary test; adapter-only import |
| Optional extra breaks default install or CI | Import test without extras in CI matrix |
| Nondeterminism from thread scheduling | Pinned `n_jobs`, fixed seeds, determinism test |
| Model artifacts treated as durable | §8 policy written into the manifest and ADR |

---

## 13. Dependencies

**Required:** SPRINT_039 dataset envelope with persisted fold roles and fingerprint.

**Not required:** reports, dashboard, trees, networks, robustness experiments.

---

## 14. Quality gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

---

## 15. Post-sprint direction

Sprint 041 renders these envelopes as an offline HTML report. Metrics schema should be considered
frozen once S041 consumes it — a later rename forces a report migration.
