# Sprint 039 — Wave 0 Decisions

Binding decisions for Predictive Research Dataset Foundation (Phase 10A). Date: 2026-08-26.
Locked 2026-08-26: maintainer chose **synthetic fixtures only** for CI (D-S039-CI-dataset)
and **optional ML extras + dedicated CI job** (D-S039-extras). Remaining slice, leakage,
fingerprint, storage, artifact, and PR-sequence rules are locked from `SPRINT_039.md` and
ROADMAP §13A.

Basis: `SPRINT_039.md`, `ROADMAP.md` §13A, ADR-0013, ADR-0020, IDEA-014 (out of scope this
sprint). Architecture source: `docs/adr/ADR-0023-predictive-research-boundary.md`
(ACCEPTED 2026-08-26).

---

## D-S039-01 — Problem statement

The framework can compute analytical outputs and measure what happened after an event. It
cannot yet state a **learning problem**: declared inputs, a target, and a split that makes
an out-of-sample claim honest.

S039 turns `AnalysisFrame` columns plus `compute_forward_outcomes_for_horizons` into a
persisted, fingerprinted supervised-learning dataset. **Nothing is trained.** A leaking
dataset would make every downstream Phase 10 sprint worthless, so the dataset contract
earns its own review.

This is a **research methodology**, not a trading capability.

---

## D-S039-02 — Sprint branch and PR base

```text
Integration branch: sprint/predictive-research-foundation
Working branches:   feat/ | fix/ | docs/ | test/  (not nested under sprint/)
PR base:            sprint/predictive-research-foundation  (never main until sprint integration)
```

Working-branch PRs squash-merge into the sprint branch. When S039 is complete, one
integration PR goes `sprint/predictive-research-foundation` → `main`. Later Phase 10
sprints (S040–S044) each open their own `sprint/<slug>` from updated `main`. Do not
open working PRs against `main`.

---

## D-S039-03 — Sprint slice

**This sprint ships exactly:** a declarative predictive-study spec, a feature matrix with
labels and availability columns, purged + embargoed walk-forward fold roles, a persisted
envelope with manifest + fingerprint, a thin CLI, and leakage regression tests.

| Order | Slice | Why |
|-------|--------|-----|
| 1 | Wave 0 + ADR-0023 | Binding boundary before any code |
| 2 | Feature / label / study specs | Declared contracts, not DataFrame dumping |
| 3 | Matrix construction | AnalysisFrame columns + reused forward outcomes |
| 4 | Purged walk-forward | Fold roles as persisted data |
| 5 | Persistence + CLI | Fingerprinted envelope under workspace storage |
| 6 | Leakage tests + docs | Prove the guards; close the sprint |

**Not this sprint:** estimators, ML dependencies, reports, dashboards, IDEA-014 promotion,
multi-instrument datasets, NQ as acceptance.

---

## D-S039-04 — Methodology boundary

Phase 10 answers *is there predictable structure in these features?* — not *should we
trade this?*

**Locked:** no path from this package into trading capabilities.

```text
no signals
no strategy/
no signal_model/
no simulation
no promotion to Market Analysis components (IDEA-014 → S044 gate / ADR-0024)
```

Predictive Research is a new methodology alongside Signal / Strategy / Robustness research.
It consumes Market Analysis outputs as features and Phase 5 forward outcomes as labels. It
does not extend Strategy Research or Execution.

---

## D-S039-05 — Package and import policy

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

**Locked:** `research/predictive/` imports **polars**, **numpy**, and framework contracts
only. No scikit-learn, XGBoost, LightGBM, CatBoost, or torch in domain code.

ML libraries live in `infrastructure/ml/<lib>/` behind a protocol (S040+). Missing extra
raises an explicit framework error naming the extra — never a raw `ImportError`.

S039 adds **no** dependency to `pyproject.toml`. Architecture boundary tests enforce the
domain import rule.

---

## D-S039-06 — ML extras policy (D-S039-extras; locked)

Human lock 2026-08-26. Implementation of the extra and the CI job is **S040 work**; the
policy is binding from this sprint and is recorded in ADR-0023.

**Locked:**

```text
ML libraries are optional extras — never runtime dependencies of the default install
Extra names:  ml  (sklearn, S040) → later ml-trees (S042), dl (S043)
Default install has none of them
Standard CI stays extra-free
A dedicated CI job installs extras `ml` so the ML path is still covered
Do not put scikit-learn in the default `dev` dependency-group / extra
```

---

## D-S039-07 — Features and lineage

A feature is a declared analysis output, not an arbitrary column.

```text
FeatureSpec
  component_id     ComponentId
  parameters       CanonicalParameters
  output_id        OutputId
  alias            str
  transform        NONE | LOG | DIFF | PCT_CHANGE | RANK       (bounded set)
```

The builder maps `FeatureSpec` onto `AnalysisFrameColumnSpec` / `OutputRef` lineage via the
existing `AnalysisFrameRequest` path. `column_lineage` already carries an `OutputRef` per
column; those refs are hashed into the dataset fingerprint.

**Locked:** the builder **never recomputes analysis**. Feature values come from already-built
`AnalysisFrame` columns.

---

## D-S039-08 — Labels and incomplete outcomes

**Locked:** reuse `compute_forward_outcomes_for_horizons`. Do not reimplement outcome logic.

```text
LabelKind.REGRESSION       target = forward_return at horizon h
LabelKind.BINARY           target = 1 if forward_return > threshold else 0
LabelKind.TERNARY          target = -1 / 0 / +1 with a declared neutral band
```

Rows with `outcome_status != COMPLETE` are **excluded** from labelled rows and **counted**
in the manifest. They never receive a label.

Labels are always taken at a **single declared horizon** per dataset. Multi-horizon studies
build multiple datasets sharing one spec family.

Every matrix row carries `detected_at`, `available_at`, and `label_end_at`. Those three
timestamps make purging computable.

---

## D-S039-09 — Splits and fold roles

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
3. **Purge:** training rows whose `label_end_at` falls inside the test window are not TRAIN.
4. **Embargo:** additionally hold out training rows within `embargo_span` after the test
   window (EXPANDING mode, where later folds reuse earlier data).
5. Assign persisted `fold_id` and `fold_role`: `TRAIN` / `TEST` / `PURGED` / `EMBARGOED`.

**Locked:** purged and embargoed rows are **retained with a role label**, not deleted. S041
must be able to show how much data each guard removed.

---

## D-S039-10 — Preprocessing stays out of the builder

**Locked:** scaling, encoding, imputation, and any other fitted transform do **not** belong
in the dataset builder. Fitting a scaler here would leak test-fold statistics into training
before a single model exists.

Training-fold-only preprocessing is an S040 contract, fitted inside each fold on TRAIN rows
only. Rows with role `PURGED` or `EMBARGOED` are never passed to `fit()`.

---

## D-S039-11 — Dataset fingerprint

**Locked:** the fingerprint hashes:

```text
study spec (definition_hash)
feature lineage (OutputRef per column)
DatasetRef
time range
```

It **never** hashes materialized frame bytes. Frame-byte hashes are unstable across Polars
versions and would make an unchanged spec look like a new dataset.

`dataset_id` derives from the definition hash, matching the `derive_run_id` pattern used by
Signal Research. Rebuilding an unchanged spec yields a byte-identical fingerprint.

---

## D-S039-12 — Storage layout

```text
<workspace>/research/predictive_research/
  datasets/{dataset_id}/
    manifest.json          spec, fingerprints, row counts, exclusion counts
    features.parquet       feature matrix + label + availability + fold columns
    folds.json             resolved fold boundaries
```

Predictive datasets are persisted separately from Signal and Strategy Research runs. Paths
are registered in `infrastructure/storage/paths.py`.

---

## D-S039-13 — CI dataset (D-S039-CI-dataset; locked)

Human lock 2026-08-26.

**Locked:** S039 acceptance uses **synthetic fixtures only**.

```text
S039 acceptance does NOT require a continuous NQ run
No optional NQ demo script in this sprint
Leakage suite and E2E fingerprint round-trip run on deterministic synthetic fixtures
```

A later sprint may add an NQ demo; it is not a gate for S039.

---

## D-S039-14 — Artifact policy

S039 trains nothing. The policy is still binding for Phase 10 so S040 does not reopen it.

**Locked:**

```text
Durable facts:     predictions + metrics (Parquet / JSON)
Fitted model blobs: opaque, version-tagged (library name + version)
Not portable across library upgrades
Reproduce a run by re-fitting from the manifest — never by deserializing a blob
```

No workflow may depend on reloading a fitted blob. A model registry stays deferred.

---

## D-S039-15 — Out of scope (S039)

- Estimators, training, predictions, metrics (→ S040).
- scikit-learn, XGBoost, LightGBM, CatBoost, torch — no ML dependency in this sprint.
- The `ml` extra and the dedicated CI job that installs it (policy here; work in S040).
- Reports and dashboards (→ S041, S044).
- Feature selection, dimensionality reduction, automated feature engineering.
- Promotion of anything to a Market Analysis component (IDEA-014 → S044).
- Multi-instrument / cross-sectional datasets. One instrument per dataset.
- Risk-adjusted regression target `forward_return / atr_at_entry` (not a default; deferred).
- Continuous NQ run or NQ demo script (D-S039-CI-dataset).

---

## D-S039-16 — PR sequence

Locked from `SPRINT_039.md` §10. Each PR targets `sprint/predictive-research-foundation`.

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 1 | `docs/predictive-research-planning` | T001–T002 Wave 0 + ADR-0023 |
| 2 | `feat/predictive-feature-label-specs` | T003–T005 specification contracts |
| 3 | `feat/predictive-feature-matrix` | T006–T009 matrix construction |
| 4 | `feat/predictive-purged-walk-forward` | T010–T012 splitting |
| 5 | `feat/predictive-dataset-persistence` | T013–T017 envelope, paths, CLI |
| 6 | `test/predictive-leakage-guards` | T018–T019 leakage suite |
| 7 | `docs/predictive-foundation-closure` | T020 documentation |

Wait for squash-merge of PR *n* before opening a dependent PR *n+1*.

---

## D-S039-17 — Risk-adjusted label (deferred)

`SPRINT_039.md` §5 named `forward_return / atr_at_entry` as a Wave 0 decision, not a default.

**Locked:** S039 labels are `forward_return` at one horizon, plus binary / ternary derived
from that return. ATR-adjusted regression is **out of scope** until a later sprint names it.

---

## Wave 0 checklist status

- [x] Confirm sprint branch: `sprint/predictive-research-foundation` (D-S039-02)
- [x] Slice: dataset foundation only; nothing trained (D-S039-03)
- [x] Methodology boundary: no signals / strategy / signal_model / simulation (D-S039-04)
- [x] Domain imports: polars + numpy + framework contracts only (D-S039-05)
- [x] D-S039-extras: optional extras + dedicated CI job with `ml` (D-S039-06)
- [x] Features: declared FeatureSpec + OutputRef lineage; builder never recomputes (D-S039-07)
- [x] Labels: reuse forward outcomes; incomplete excluded and counted (D-S039-08)
- [x] Splits: purged + embargoed walk-forward; roles persisted not deleted (D-S039-09)
- [x] Preprocessing out of the dataset builder (D-S039-10)
- [x] Fingerprint hashes spec + lineage + DatasetRef + range, never frame bytes (D-S039-11)
- [x] Storage under `<workspace>/research/predictive_research/datasets/{dataset_id}/` (D-S039-12)
- [x] D-S039-CI-dataset: synthetic fixtures only; no NQ acceptance (D-S039-13)
- [x] Artifact policy: predictions + metrics durable; blobs opaque / re-fit to reproduce (D-S039-14)
- [x] Out of scope S039 confirmed (D-S039-15)
- [x] PR sequence from SPRINT_039 §10 (D-S039-16)
- [x] ATR-adjusted label deferred (D-S039-17)
