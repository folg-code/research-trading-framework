# ADR-0023 — Predictive Research Domain Boundary

## Status

ACCEPTED (Sprint 039)

Approved-by: Project Maintainer (2026-08-26) — open S039; synthetic CI fixtures
only; optional `ml` extra with a dedicated CI job (not in default `dev`).

## Context

Sprints 008–010 deliver Signal Research computation, persistence and read-only analytics
(ADR-0011–0013). Sprint 017 adds a methodology layer on top of that kernel (ADR-0020).
Market Analysis already produces aligned `AnalysisFrame` columns with `OutputRef` lineage.
Forward outcomes already exist (`compute_forward_outcomes_for_horizons`).

What is missing is a **learning-problem contract**: declared features, a label, and a split
that makes an out-of-sample claim honest. ROADMAP §13A (Phase 10) introduces Predictive
Research as a new methodology for that contract — Sprints 039–044.

Without a recorded boundary, Phase 10 can drift in three ways that are expensive to undo:

1. ML libraries leak into domain code or the default install / standard CI.
2. Temporal leakage (feature availability, label-horizon overlap, or preprocessing fitted
   on all rows) is treated as a training detail instead of a dataset invariant.
3. Predictions are treated as signals, or fitted model blobs are treated as portable
   artifacts.

Sprint 039 trains nothing. The extras, leakage, and artifact rules are still recorded here
so S040 does not reopen them.

Wave 0 locks: `docs/planning/sprints/S039_WAVE0_DECISIONS.md` (2026-08-26). Human forks:
synthetic CI fixtures only (D-S039-CI-dataset); optional extras + dedicated CI job
(D-S039-extras).

## Decision

### 1. Methodology, not a trading capability

Predictive Research answers *is there predictable structure in these features?* — not
*should we trade this?*

It consumes Market Analysis outputs as **features** and Phase 5 forward outcomes as
**labels**. It does not extend Strategy Research or Execution.

The domain must not:

```text
emit signals
import strategy/
import signal_model/
run simulation
promote a trained model to a Market Analysis component   (IDEA-014 → S044 / ADR-0024)
```

A trained model is never promoted to a tradable signal inside Phase 10.

### 2. Package and import boundary

```text
research/predictive/          domain: specs, matrix, splits, estimator protocol (S040+)
research/datasets/predictive  envelope + repository
infrastructure/ml/<lib>/      adapters only (S040+: sklearn; later trees / dl)
application/predictive_research/
scripts/predictive_research/  thin CLI
```

`research/predictive/` imports **polars**, **numpy**, and framework contracts only.
Domain code must not import scikit-learn, XGBoost, LightGBM, CatBoost, or torch.

Feature values come from `AnalysisFrame` columns. The dataset builder **never recomputes
analysis**. Labels reuse `compute_forward_outcomes_for_horizons`; the calculator is not
reimplemented.

### 3. Dependency and extras policy (D-S039-extras)

ML libraries are **optional extras**, never runtime dependencies of the default install.

```text
ml         scikit-learn          S040
ml-trees   XGBoost / LightGBM / CatBoost   S042
dl         torch                 S043
```

```text
Default install has none of them
Standard CI stays extra-free
A dedicated CI job installs extras `ml` so the ML path is still covered
Do not put scikit-learn in the default `dev` dependency-group / extra
```

S039 adds no ML dependency and no extra. The extra and the dedicated CI job are S040 work;
this ADR is the policy source.

Missing extra: requesting a family whose extra is not installed raises an **explicit
framework error naming the extra**, never a raw `ImportError`.

### 4. Leakage policy

Leakage is a dataset invariant, enforced by tests, not a training-time courtesy.

**Features.** Declared `FeatureSpec` mapped onto `AnalysisFrameColumnSpec` / `OutputRef`
lineage. No feature column may have `available_at` later than the row's `detected_at`.
The builder does not invent columns.

**Labels.** Rows with `outcome_status != COMPLETE` are excluded from labelled rows and
counted in the manifest. They never receive a label.

**Availability.** Every matrix row carries `detected_at`, `available_at`, and
`label_end_at`. Without `label_end_at` the fold planner cannot know which training rows
still see the test period.

**Splits.** Purged + embargoed walk-forward is a first-class domain object. Fold roles
`TRAIN` / `TEST` / `PURGED` / `EMBARGOED` are **persisted columns**, not deleted rows.
Label-horizon overlap between train and test is purged, not tolerated. Embargo holds out
the declared span after each test window in EXPANDING mode.

**Preprocessing.** Scaling, encoding, imputation and other fitted transforms do **not**
belong in the dataset builder. They are fitted on TRAIN rows of each fold only (S040).
`PURGED` and `EMBARGOED` rows are never passed to `fit()`.

S039 leakage regressions (counter-fixtures required) live in `SPRINT_039.md` §9.

### 5. Fingerprint

The dataset fingerprint hashes **spec + feature lineage + DatasetRef + time range**.
It never hashes materialized frame bytes (unstable across Polars versions).

`dataset_id` derives from the definition hash (same pattern as Signal Research
`derive_run_id`). An unchanged spec rebuilds to a byte-identical fingerprint. Any spec
field change produces a different fingerprint.

### 6. Storage

```text
<workspace>/research/predictive_research/
  datasets/{dataset_id}/     S039: manifest, features.parquet, folds.json
  runs/{run_id}/             S040+: manifest, predictions, metrics, opaque model blobs
```

Predictive artifacts are persisted separately from Signal and Strategy Research runs.

### 7. Artifact policy

S039 persists datasets only. Phase 10 run artifacts (S040+) follow this rule even though
S039 trains nothing:

```text
Durable facts:      predictions + metrics (Parquet / JSON)
Fitted model blobs: opaque, version-tagged (library name + version)
Not portable across library upgrades
Reproduce by re-fitting from the manifest — never by deserializing a blob
```

No workflow may depend on reloading a fitted blob. A model registry stays deferred.

### 8. CI dataset (D-S039-CI-dataset)

S039 acceptance uses **synthetic fixtures only**. It does not require a continuous NQ run
and does not ship an optional NQ demo script.

### 9. First-slice limits

One instrument per dataset. One declared label horizon per dataset (multi-horizon studies
build multiple datasets). ATR-adjusted regression (`forward_return / atr_at_entry`) is
not in the S039 default label set.

## Consequences

### Positive

- Domain stays extra-free; standard CI does not pay for sklearn / trees / torch.
- Leakage guards are dataset facts (fold roles, availability columns, exclusion counts),
  not comments in a training script.
- Feature lineage is reproducible (`OutputRef` in the fingerprint), not aspirational.
- S040 can add estimators without reopening storage, split, or extras policy.
- Predictions and metrics remain readable if a library upgrade invalidates blobs.

### Negative

- Two CI jobs from S040 onward (extra-free default + dedicated `ml` job).
- Authors cannot dump arbitrary DataFrame columns as features; they must declare
  `FeatureSpec`.
- Fitted blobs are convenience only; inspection after a library bump requires a re-fit.
- One instrument and one horizon per dataset until a later sprint widens the grain.
- IDEA-014 promotion is blocked until S044 / ADR-0024.

## References

- `docs/planning/sprints/S039_WAVE0_DECISIONS.md`
- `docs/planning/sprints/SPRINT_039.md`
- `docs/planning/sprints/SPRINT_040.md` (estimator seam, extras implementation, run envelope)
- `docs/planning/ROADMAP.md` §13A
- `docs/adr/ADR-0013-signal-research-analytics-boundary.md`
- `docs/adr/ADR-0020-model-research-methodology-mvp.md`
- `docs/adr/ADR-MA-010-external-analytical-libraries.md` (optional-library precedent)
- `docs/planning/IDEA_INBOX.md` (IDEA-014, IDEA-003)
