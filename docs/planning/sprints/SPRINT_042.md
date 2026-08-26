# Sprint 042 — Tree-Based Predictive Models (Phase 10B)

## Metadata

```text
Sprint: 042
Phase: Phase 10B — Tree-Based Predictive Models
Status: IN PROGRESS (Wave 4)
Planned Start: 2026-08-26
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_040 (estimator seam on main #319); SPRINT_041 report panels after #325
Sprint Branch: sprint/predictive-tree-models
Task branch convention: feat/ | fix/ | docs/ | test/
Wave 0 decisions: docs/planning/sprints/S042_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/planning/ROADMAP.md (§13A Phase 10B)
  - docs/adr/ADR-0023 (Predictive Research boundary — S039)
  - docs/adr/ADR-0019-robustness-research-mvp.md (bounded search precedent)
  - docs/planning/sprints/SPRINT_040.md (PredictiveEstimator protocol)
```

---

## 0. Slice choice

Gradient-boosted trees are the default choice for tabular financial features, and for good reason:
they handle non-linearity and feature interaction without the data volume a network demands. They
are also the fastest way to overfit a few thousand samples into a beautiful in-sample curve.

The estimator seam from S040 means adding three libraries changes no domain code. That leaves the
sprint free to focus on what actually needs care: **determinism**, **bounded search** and **honest
importance**.

Bounded search is the load-bearing constraint. An unbounded hyperparameter sweep against a
walk-forward split is a machine for producing overfit results that look validated, so the candidate
count is declared up front and recorded in the manifest, following the `CandidateBounds` precedent
already used in Signal Research and the grid caps in Robustness.

**Out of scope:** networks, SHAP, automated feature engineering, portfolio construction.

---

## 1. Sprint Goal

```text
PredictiveDatasetEnvelope (S039)
    ↓
EstimatorSpec family = xgboost | lightgbm | catboost
    ↓
bounded candidate set (declared, capped, fingerprinted)
    ↓
per fold: inner train/validation split → select → fit → predict TEST
    ↓
PredictiveRunEnvelope + study leaderboard across families
    ↓
report extended with importance and leaderboard panels
```

Success: three tree libraries run through the unchanged protocol, produce reproducible predictions,
and are compared against each other and the S040 baselines on one dataset fingerprint.

---

## 2. In scope

- [x] Optional extra `ml-trees` = XGBoost, LightGBM, CatBoost.
- [x] Three adapters in `infrastructure/ml/trees/`, one protocol, no domain change.
- [x] Determinism configuration enforced by the adapter (§4).
- [x] `CandidateSetSpec` — declared, capped hyperparameter candidates.
- [x] Inner train/validation selection **inside** each training fold (§5).
- [x] Native importance (gain / split) plus out-of-sample permutation importance.
- [x] Study leaderboard comparing estimator families on one dataset fingerprint.
- [ ] Report panels: importance, leaderboard, candidate-selection trace.
- [x] Overfitting diagnostics: train-fold versus test-fold metric gap.

## 3. Out of scope

- Neural estimators (→ S043).
- SHAP values — deferred, see §9.
- Unbounded or adaptive search (Bayesian, genetic, Optuna-style).
- Ensembling or stacking across families.
- GPU training.
- Cross-study leaderboards spanning different dataset fingerprints.

---

## 4. Determinism contract

Tree libraries are deterministic only when configured to be. The adapter owns that, not the caller:

```text
Fixed random seed on every estimator
Single-threaded or pinned thread count — thread count recorded in the manifest
Deterministic histogram / tree construction methods only
Non-deterministic options rejected at spec validation with an explicit error
Library name and version recorded through describe()
```

A reproducibility test fits the same spec twice and asserts byte-identical predictions. Where a
library cannot guarantee determinism at a given thread count, the adapter pins threads rather than
accepting drift — reproducibility outranks throughput in a research framework.

---

## 5. Bounded candidate selection

```text
CandidateSetSpec
  candidates        tuple[EstimatorSpec, ...]      explicitly declared
  max_candidates    int                            hard cap, validated
  selection_metric  metric identifier
  inner_split       fraction | fold count          within the training fold only
```

Selection procedure per outer fold:

1. Split the outer `TRAIN` rows chronologically into inner train and inner validation.
2. Fit every candidate on inner train, score on inner validation.
3. Select the best candidate by `selection_metric`.
4. Refit the winner on the full outer `TRAIN` rows.
5. Predict the outer `TEST` rows once.

The outer test fold is touched exactly once per fold, after selection is finished. Selection may
choose a different candidate per fold — that variation is itself a stability signal and is recorded
in the selection trace.

Early stopping, where the library supports it, uses the inner validation split only. Using the outer
test fold as an early-stopping set is the single most common leak in boosted-tree research; spec
validation rejects any configuration that would allow it.

---

## 6. Importance and overfitting diagnostics

### Importance

```text
Native importance     gain / split count, per library, reported as-is
Permutation importance  computed on TEST rows, seeded, with repeat count
```

Native importance is reported but not trusted for conclusions: it is computed on training data and
biased toward high-cardinality features. Permutation importance on out-of-sample rows is the one the
report emphasizes, and both are shown side by side so the divergence is visible.

### Overfitting gap

Every run reports the primary metric on training rows and test rows per fold. A large, consistent
gap is the honest description of a boosted model that has memorized its folds, and it belongs in the
report next to the headline number.

---

## 7. Task breakdown

### Wave 0 — Planning

| Task | Description | Status |
|------|-------------|--------|
| S042-T001 | Wave 0 decisions (library set, thread policy, candidate caps) | DONE |

### Wave 1 — Adapters

| Task | Description | Status |
|------|-------------|--------|
| S042-T002 | Optional extra `ml-trees` + missing-extra errors | DONE |
| S042-T003 | XGBoost adapter (regression + classification) | DONE |
| S042-T004 | LightGBM adapter (regression + classification) | DONE |
| S042-T005 | CatBoost adapter (regression + classification) | DONE |
| S042-T006 | Determinism enforcement + rejection of non-deterministic options | DONE |
| S042-T007 | Reproducibility test: identical predictions across repeated fits | DONE |

### Wave 2 — Bounded selection

| Task | Description | Status |
|------|-------------|--------|
| S042-T008 | `CandidateSetSpec` + cap validation | DONE |
| S042-T009 | Inner train/validation split within the training fold | DONE |
| S042-T010 | Per-fold candidate selection + refit on full train fold | DONE |
| S042-T011 | Early stopping bound to inner validation; outer-test usage rejected | DONE |
| S042-T012 | Selection trace persisted (candidate scores per fold) | DONE |

### Wave 3 — Importance and diagnostics

| Task | Description | Status |
|------|-------------|--------|
| S042-T013 | Native importance extraction per library, normalized shape | DONE |
| S042-T014 | Out-of-sample permutation importance (seeded, repeated) | DONE |
| S042-T015 | Train-versus-test metric gap per fold | DONE |

### Wave 4 — Leaderboard and report

| Task | Description | Status |
|------|-------------|--------|
| S042-T016 | Study leaderboard across families on one dataset fingerprint | DONE |
| S042-T017 | Report panel: importance (native + permutation) | DONE |
| S042-T018 | Report panel: leaderboard including S040 baselines | DONE |
| S042-T019 | Report panel: candidate selection trace + overfitting gap | DONE |

### Wave 5 — Closure

| Task | Description | Status |
|------|-------------|--------|
| S042-T020 | Comparison study on the canonical dataset (baselines + three families) | DONE |
| S042-T021 | Import test: framework usable without `ml-trees` | DONE |
| S042-T022 | Docs: RESEARCH_METHODOLOGIES, MODULE_MAP, CURRENT_STATUS | TODO |

**Progress:** 21 / 22 tasks

---

## 8. Recommended PR sequence

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 1 | `docs/predictive-tree-models-planning` | T001 Wave 0 |
| 2 | `feat/predictive-xgboost-adapter` | T002–T003, T006–T007 first adapter + determinism |
| 3 | `feat/predictive-lightgbm-catboost-adapters` | T004–T005 remaining adapters |
| 4 | `feat/predictive-bounded-candidate-selection` | T008–T012 selection |
| 5 | `feat/predictive-importance-diagnostics` | T013–T015 importance + gap |
| 6 | `feat/predictive-study-leaderboard` | T016 leaderboard |
| 7 | `feat/predictive-report-tree-panels` | T017–T019 report panels |
| 8 | `docs/predictive-tree-models-closure` | T020–T022 study + docs |

Each PR targets `sprint/predictive-tree-models`.

---

## 9. SHAP deferral

SHAP is the obvious next request and is deliberately excluded. It adds a dependency, is expensive on
large test folds, and its interpretation for correlated financial features is subtle enough to
mislead more than permutation importance does. Revisit only when a concrete question cannot be
answered by permutation importance; record the decision in the Wave 0 document if promoted.

---

## 10. Acceptance criteria

1. Three tree families run through the unchanged `PredictiveEstimator` protocol.
2. No domain module changed to accommodate a library — adapters only.
3. Repeated fits of one spec produce byte-identical predictions.
4. Non-deterministic library options are rejected at validation with a named error.
5. Candidate count is capped, validated and recorded in the manifest.
6. Early stopping cannot reference the outer test fold; a test proves the rejection.
7. Selection trace records every candidate score per fold.
8. Permutation importance is computed out of sample and displayed beside native importance.
9. Train-versus-test metric gap is reported per fold.
10. Leaderboard compares families and S040 baselines on one dataset fingerprint.
11. Framework imports and non-tree tests pass without the `ml-trees` extra.
12. CI green: `ruff check`, `ruff format --check`, `mypy`, `pytest`.

---

## 11. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Search space grows until results are overfit | Hard cap in `CandidateSetSpec`, recorded in manifest |
| Early stopping leaks the test fold | Inner validation only; validation rejects the alternative |
| Non-reproducible results from threading | Pinned threads, seeds, repeated-fit test |
| Native importance drives wrong conclusions | Permutation importance emphasized; both shown together |
| Three heavy libraries slow CI | Extra is opt-in; fixture datasets kept small |
| Library version drift changes results silently | Version in run fingerprint; upgrade means a new run id |
| Tree results treated as a strategy | Phase 10 has no verdict; promotion gate stays in S044 |

---

## 12. Dependencies

**Required:** S040 estimator seam and metrics (on `main` #319).

**Required for Wave 4 only:** S041 panel registry (integration PR #325).

**Not required:** networks, dashboard, robustness experiments.

---

## 13. Quality gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

---

## 14. Post-sprint direction

Sprint 043 adds neural estimators through the same seam. The leaderboard built here is what makes
that comparison meaningful — if networks cannot beat these trees, the leaderboard will say so
plainly.
