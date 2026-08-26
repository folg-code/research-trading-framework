# Sprint 039 — Predictive Research Dataset Foundation (Phase 10A)

## Metadata

```text
Sprint: 039
Phase: Phase 10A — Predictive Research Foundation
Status: COMPLETE
Planned Start: 2026-08-26
Planned End: 2026-08-26
Sprint Goal Owner: Project Maintainer
Depends On: S036 audit (#288), S037 component libraries + DSL (#296), S038 Session Range (#300) — all on main
Sprint Branch: sprint/predictive-research-foundation
Task branch convention: feat/ | fix/ | docs/ | test/ (separate prefix, not nested under sprint ref)
Wave 0 decisions: docs/planning/sprints/S039_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/adr/ADR-0023-predictive-research-boundary.md (ACCEPTED)
  - docs/planning/ROADMAP.md (§13A Phase 10)
  - docs/adr/ADR-0013-signal-research-analytics-boundary.md
  - docs/adr/ADR-0020 (model research methodology)
  - docs/planning/IDEA_INBOX.md (IDEA-014, IDEA-003)
Track choice: Phase 10 opens the AI/ML track named in CURRENT_STATUS §11; IDEA-014 promotion stays out of scope
```

---

## 0. Slice choice

The framework can already compute analytical outputs and measure what happened after an event. What
it cannot do is state a **learning problem**: here are the inputs, here is the target, here is the
split that makes an out-of-sample claim honest.

Two contracts already carry most of the weight:

```text
AnalysisFrame        aligned columns + column_lineage (OutputRef per column)
forward outcomes     forward_return / mfe / mae + outcome_status per (occurrence, horizon)
```

This sprint turns those into a persisted, fingerprinted supervised-learning dataset. Nothing is
trained. That is deliberate: a leaking dataset makes every downstream sprint worthless, so the
dataset contract earns its own review.

**Out of scope:** any estimator, any ML dependency, any report, any model artifact.

---

## 1. Sprint Goal

```text
Published OHLCV DatasetRef + declared analysis columns
    ↓
FeatureMatrixSpec (features) × LabelSpec (target)
    ↓
build_predictive_dataset
    ↓
feature matrix rows keyed (entity_id, horizon_bars) + label column + availability columns
    ↓
PurgedWalkForwardSplitSpec → fold assignment (train / purge / embargo / test)
    ↓
PredictiveDatasetEnvelope persisted with manifest + fingerprint
```

Success: a maintainer declares a study in YAML, runs one command, and receives a persisted dataset
whose folds are provably free of temporal leakage — verified by tests, not by inspection.

---

## 2. In scope

- [x] `research/predictive/` domain package (polars + numpy only, no ML libraries).
- [x] `FeatureSpec` / `FeatureMatrixSpec` mapping declared features onto `AnalysisFrameColumnSpec`.
- [x] `LabelSpec` with regression and classification variants derived from forward outcomes.
- [x] Feature matrix builder producing one normalized Polars frame.
- [x] `PurgedWalkForwardSplitSpec` + fold planner (rolling and expanding).
- [x] `PredictiveDatasetEnvelope`, manifest, repository and storage paths.
- [x] Dataset fingerprint covering spec, feature lineage, dataset ref and time range.
- [x] Declarative YAML/JSON study spec with `definition_hash`, mirroring
      `SignalResearchDefinitionSpec`.
- [x] CLI `scripts/predictive_research/build_predictive_dataset.py`.
- [x] Leakage regression tests on deterministic fixtures.
- [x] ADR-0023 — Predictive Research domain boundary and leakage policy.

## 3. Out of scope

- Estimators, training, predictions, metrics (→ S040).
- scikit-learn, XGBoost, LightGBM, CatBoost, torch — no ML dependency is added in this sprint.
- Reports and dashboards (→ S041, S044).
- Feature selection, dimensionality reduction, automated feature engineering.
- Promotion of anything to a Market Analysis component (IDEA-014 → S044 gate document).
- Multi-instrument / cross-sectional datasets. One instrument per dataset in the first slice.

---

## 4. Domain boundary

```text
research/predictive/spec.py             study spec, definition hash
research/predictive/features.py         FeatureSpec, FeatureMatrixSpec
research/predictive/labels.py           LabelSpec, label derivation from forward outcomes
research/predictive/matrix.py           feature matrix builder
research/predictive/splitting.py        purged + embargoed walk-forward fold planner
research/datasets/predictive.py         PredictiveDatasetEnvelope + repository
application/predictive_research/        build orchestration
scripts/predictive_research/            thin CLI
```

### Binding rules

```text
research/predictive/ imports polars, numpy and framework contracts — nothing else
Feature values come from AnalysisFrame columns; the builder never recomputes analysis
Labels come from research/outcomes/ — the calculator is reused, not reimplemented
Rows with outcome_status != COMPLETE are excluded explicitly and counted in the manifest
Fold assignment is data, not code — it is persisted and fingerprinted
No preprocessing (scaling, encoding, imputation) happens here; it belongs to the training fold
```

The last rule matters: fitting a scaler in the dataset builder would leak test-fold statistics into
training before a single model exists.

---

## 5. Feature and label contracts

### Features

A feature is a declared analysis output, not an arbitrary column:

```text
FeatureSpec
  component_id     ComponentId
  parameters       CanonicalParameters
  output_id        OutputId
  alias            str
  transform        NONE | LOG | DIFF | PCT_CHANGE | RANK       (bounded set)
```

The builder resolves specs through the existing `AnalysisFrameRequest` path, so `column_lineage`
already carries an `OutputRef` per column. Those refs are hashed into the dataset fingerprint — this
is how feature lineage becomes reproducible rather than aspirational.

### Labels

```text
LabelKind.REGRESSION       target = forward_return at horizon h
LabelKind.BINARY           target = 1 if forward_return > threshold else 0
LabelKind.TERNARY          target = -1 / 0 / +1 with a declared neutral band
```

Optional risk-adjusted regression target `forward_return / atr_at_entry` is a Wave 0 decision, not a
default. Labels are always taken at a single declared horizon per dataset; multi-horizon studies
build multiple datasets sharing one spec family.

### Availability columns

Every row carries `detected_at`, `available_at` and `label_end_at`. Those three timestamps are what
makes purging computable — without `label_end_at` the fold planner cannot know which training rows
still "see" the test period.

---

## 6. Splitting contract

```text
PurgedWalkForwardSplitSpec
  mode              ROLLING | EXPANDING
  fold_count        int
  test_span         duration
  embargo_span      duration
  min_train_rows    int
```

Fold construction:

1. Order rows by `available_at`.
2. Cut chronological test windows per `mode` and `fold_count`.
3. **Purge**: drop training rows whose `label_end_at` falls inside the test window. A 60-bar label
   means the last 60 bars before a test fold are contaminated and must go.
4. **Embargo**: additionally drop training rows within `embargo_span` after the test window, for
   expanding mode where later folds reuse earlier data.
5. Assign `fold_id` and `fold_role` (`TRAIN`, `TEST`, `PURGED`, `EMBARGOED`) as persisted columns.

Purged and embargoed rows are **retained with a role label** rather than deleted, so the report in
S041 can show exactly how much data each guard removed.

---

## 7. Storage

```text
<workspace>/research/predictive_research/
  datasets/{dataset_id}/
    manifest.json          spec, fingerprints, row counts, exclusion counts
    features.parquet       feature matrix + label + availability + fold columns
    folds.json             resolved fold boundaries
```

`dataset_id` derives from the definition hash, matching the `derive_run_id` pattern already used by
Signal Research.

---

## 8. Task breakdown

### Wave 0 — Planning

| Task | Description | Status |
|------|-------------|--------|
| S039-T001 | Wave 0 decisions (`S039_WAVE0_DECISIONS.md`) | DONE |
| S039-T002 | ADR-0023 — Predictive Research boundary, leakage policy, dependency policy | DONE |

### Wave 1 — Specification contracts

| Task | Description | Status |
|------|-------------|--------|
| S039-T003 | `FeatureSpec` / `FeatureMatrixSpec` + validation | DONE |
| S039-T004 | `LabelSpec` (regression, binary, ternary) + validation | DONE |
| S039-T005 | `PredictiveStudySpec` YAML/JSON loader + `definition_hash` | DONE |

### Wave 2 — Matrix construction

| Task | Description | Status |
|------|-------------|--------|
| S039-T006 | Feature matrix builder over `AnalysisFrame` columns | DONE |
| S039-T007 | Label derivation from `compute_forward_outcomes_for_horizons` | DONE |
| S039-T008 | Availability columns (`detected_at`, `available_at`, `label_end_at`) | DONE |
| S039-T009 | Row exclusion policy + counts (incomplete horizon, null features) | DONE |

### Wave 3 — Splitting

| Task | Description | Status |
|------|-------------|--------|
| S039-T010 | `PurgedWalkForwardSplitSpec` + validation (spec already in Wave 1; planner in this PR) | DONE |
| S039-T011 | Fold planner (rolling + expanding) with purge and embargo | DONE |
| S039-T012 | Fold role assignment persisted on the matrix | DONE |

### Wave 4 — Persistence and CLI

| Task | Description | Status |
|------|-------------|--------|
| S039-T013 | `PredictiveDatasetEnvelope` + manifest + repository | DONE |
| S039-T014 | Storage paths in `infrastructure/storage/paths.py` | DONE |
| S039-T015 | Dataset fingerprint (spec + feature lineage + dataset ref + range) | DONE |
| S039-T016 | `build_predictive_dataset` application workflow | DONE |
| S039-T017 | CLI `scripts/predictive_research/build_predictive_dataset.py` | DONE |

### Wave 5 — Leakage tests and closure

| Task | Description | Status |
|------|-------------|--------|
| S039-T018 | Leakage regression suite (see §9) | DONE |
| S039-T019 | End-to-end fixture test: spec → dataset → reload → identical fingerprint | DONE |
| S039-T020 | Docs: MODULE_MAP, DATA_WORKFLOWS, RESEARCH_METHODOLOGIES, CURRENT_STATUS | DONE |

**Progress:** 20 / 20 tasks

`DATA_WORKFLOWS.md` is not in the repository. T020 recorded research paths in
`MODULE_MAP.md` (package + `research/predictive_research/` subtree),
`RESEARCH_METHODOLOGIES.md`, and `ARCHITECTURE_AND_WORKFLOWS.md` §6.

---

## 9. Leakage regression suite

These tests are the reason the sprint exists. Each one fails loudly on a deliberately broken fixture:

1. No feature column has `available_at` later than the row's `detected_at`.
2. No `TRAIN` row has `label_end_at` inside any `TEST` window of the same fold.
3. Embargo removes rows in the declared span after each test window in `EXPANDING` mode.
4. Rows with `outcome_status != COMPLETE` never receive a label.
5. Fold windows are chronologically ordered and non-overlapping in `test` role.
6. Shuffling input row order does not change the resulting fold assignment.
7. Rebuilding the dataset from the same spec produces an identical fingerprint.
8. A spec change (any field) produces a different fingerprint.

---

## 10. Recommended PR sequence

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 1 | `docs/predictive-research-planning` | T001–T002 Wave 0 + ADR-0023 |
| 2 | `feat/predictive-feature-label-specs` | T003–T005 specification contracts |
| 3 | `feat/predictive-feature-matrix` | T006–T009 matrix construction |
| 4 | `feat/predictive-purged-walk-forward` | T010–T012 splitting |
| 5 | `feat/predictive-dataset-persistence` | T013–T017 envelope, paths, CLI |
| 6 | `test/predictive-leakage-guards` | T018–T019 leakage suite |
| 7 | `docs/predictive-foundation-closure` | T020 documentation |

Each PR targets `sprint/predictive-research-foundation`.

---

## 11. Acceptance criteria

1. A YAML study spec builds a persisted dataset through one CLI command.
2. `research/predictive/` imports no ML library; the architecture boundary test enforces it.
3. Every feature column resolves to an `OutputRef` recorded in the manifest.
4. Fold assignment is persisted with explicit `TRAIN` / `TEST` / `PURGED` / `EMBARGOED` roles.
5. All eight leakage regressions in §9 pass, and each has a failing counter-fixture.
6. Manifest reports row counts, exclusion counts and purge/embargo removal counts.
7. Rebuilding an unchanged spec yields a byte-identical fingerprint.
8. No dependency is added to `pyproject.toml` in this sprint.
9. CI green: `ruff check`, `ruff format --check`, `mypy`, `pytest`.
10. ADR-0023 ACCEPTED; MODULE_MAP and DATA_WORKFLOWS updated.

---

## 12. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Silent temporal leakage | §9 suite with counter-fixtures; purge/embargo as persisted data |
| Feature matrix becomes an untyped DataFrame dumping ground | Declared `FeatureSpec` only; schema validation on write |
| Duplicating outcome logic | Reuse `compute_forward_outcomes_for_horizons` verbatim |
| Sprint slips into training "just to see something" | Explicit §3; no ML dependency may appear in this sprint |
| Dataset size explosion on multi-year NQ | One instrument, one horizon per dataset; row counts in manifest |
| Fingerprint instability across polars versions | Hash the spec and lineage, never the materialized frame |

---

## 13. Dependencies

**Required:**

- `AnalysisFrame` with `column_lineage` (Sprint 004+),
- `compute_forward_outcomes_for_horizons` (Sprint 008+),
- S037 component libraries and S038 `structure.session_range` — feature breadth depends on the
  catalog; further catalog PRs (wick, distance-to-level) widen it but do not block this sprint.

**Not required:**

- Robustness experiments, Strategy Research, Phase 8 execution.

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

Sprint 040 adds the estimator protocol and the first baselines on top of this dataset. The dataset
contract must be stable before then — a change to fold semantics after S040 invalidates every
persisted run.

---

## 16. Review

Closed 2026-08-26. Working PRs #302–#308 squash-merged into `sprint/predictive-research-foundation`.
This section records outcome; it does not rewrite the plan.

### Completed

- Wave 0 decisions (`S039_WAVE0_DECISIONS.md`) and ADR-0023 ACCEPTED (#302).
- Predictive study specification contracts: `FeatureSpec` / `FeatureMatrixSpec`, `LabelSpec`
  (regression, binary, ternary), `PredictiveStudySpec` YAML/JSON loader, `definition_hash` (#303).
- Labelled feature matrix builder: `AnalysisFrame` columns, labels from
  `compute_forward_outcomes_for_horizons`, availability columns, exclusion counts (#304).
- Purged walk-forward fold planner (rolling and expanding) with persisted `TRAIN` / `TEST` /
  `PURGED` / `EMBARGOED` roles (#305).
- `PredictiveDatasetEnvelope`, manifest, fingerprint, repository, storage paths, application
  workflow, CLI `scripts/predictive_research/build_predictive_dataset.py` (#306).
- Leakage regression suite with counter-fixtures; end-to-end rebuild fingerprint identity (#307).
- As-implemented docs: `MODULE_MAP.md`, `RESEARCH_METHODOLOGIES.md`,
  `ARCHITECTURE_AND_WORKFLOWS.md` §6, `CURRENT_STATUS.md` (#308).
- All 20 tasks T001–T020 DONE. No ML library added to `pyproject.toml`.

### Not Completed

- None of the in-scope tasks. `DATA_WORKFLOWS.md` is not in the repository; T020 recorded research
  paths in `MODULE_MAP.md`, `RESEARCH_METHODOLOGIES.md`, and `ARCHITECTURE_AND_WORKFLOWS.md` §6
  instead (already noted under §8).

### Demonstrated Capability

A maintainer can declare a `PredictiveStudySpec` in YAML, run
`scripts/predictive_research/build_predictive_dataset.py`, and persist a fingerprinted dataset
envelope (`manifest.json`, `features.parquet`, `folds.json`) whose fold roles are covered by the
eight leakage regressions in §9.

### Problems Discovered

- None logged in `PROBLEM_REGISTRY.md` for this sprint. No new CRITICAL/HIGH entries.

### Decisions Required

- None. ADR-0023 is ACCEPTED. S040 Wave 0 remains a later sprint (estimator seam, optional `ml`
  extra) and is not opened here.

### Technical Debt Added

- None from S039 implementation. Phase 10 planned shortcuts already listed in `TECHNICAL_DEBT.md`
  §6 (no model registry; fitted artifacts not portable) apply to later sprints (S040+ / S044), not
  to this dataset-only slice.

### Lessons Learned

- Dataset contract and leakage tests landed before any estimator. That boundary held: `research/predictive/`
  stays on polars + numpy; architecture-boundary tests reject ML imports.
- Acceptance criterion 10 named `DATA_WORKFLOWS.md`; the repository has no such file. Future sprint
  plans should cite the docs that actually exist (`MODULE_MAP.md`, `RESEARCH_METHODOLOGIES.md`).

### Follow-up

- Sprint 040 landed as #319. Sprint 041 lands with the S041 integration PR.
- Phase 10A is complete after S041 → `main`. S042–S044 remain later Phase 10B/10C work.
