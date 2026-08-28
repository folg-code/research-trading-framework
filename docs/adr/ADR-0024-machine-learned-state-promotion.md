# ADR-0024 — Promotion Conditions for Machine-Learned Market Analysis States

## Status

ACCEPTED (Sprint 044)

Approved-by: Project Maintainer — condition-by-condition approval recorded
below, 2026-08-28.

| Condition | Approved | Note |
|---|---|---|
| 1. Artifact identity | Yes | Serialization format explicitly deferred as priced future cost |
| 2. Inference-time leakage | Yes | Enforcement mechanism stated as requirement, not yet built |
| 3. Feature lineage | Yes | No new mechanism; reuses existing `OutputRef` infrastructure |
| 4. Offline/online parity | Yes | Strict identical-values bar approved; harness not yet built |
| 5. Model registry | Yes | No registry required; content-addressed store only |

This ADR states **conditions**, not an implementation authorization. No trained
model is promoted by this document; a future sprint against the gate in
`S044_GATE.md` does that work.

## Context

IDEA-014 asks whether a trained statistical or ML model may produce a Market
Analysis **State**, the same taxonomy slot occupied today by rule-based
components (ADR-0005). It was deferred pending mature research infrastructure.

Phase 10 (Sprints 039–043) built that infrastructure without promoting
anything: a declared feature matrix with `OutputRef` lineage (ADR-0023 §4,
Sprint 039), purged and embargoed walk-forward splitting (ADR-0023 §4,
Sprint 039), and run identity recorded in a content fingerprint
(`run_fingerprint` — `PredictiveRunManifest`, Sprint 040). ADR-0023 explicitly
named this ADR as the place three remaining risks get resolved: durable
artifact serialization, inference-time feature availability, and offline/
runtime parity (ADR-0023 §7, "IDEA-014 promotion is blocked until S044 /
ADR-0024").

Sprint 042 accepted TD-021 (no model registry) and TD-022 (opaque, non-portable
fitted blobs) as debt whose repayment trigger is exactly this decision. Both
are restated, not reopened, below.

Without a written answer, promotion drifts into an implementation decision
made inside a training script rather than an architectural one made in
review — expensive to undo once a State depends on it.

## Decision

A model may be promoted to a Market Analysis State component only when **all
five** conditions below hold, verified by the tests each condition names.
Strong out-of-sample research metrics are a precondition for opening a
promotion sprint — never a substitute for satisfying them.

### 1. Training artifact identity

**Condition.** The promoted artifact is identified by a fingerprint covering
the training dataset, the estimator spec, the seed, and the exact library
versions used to fit it — the same fields already hashed into
`run_fingerprint` (`compute_run_fingerprint`,
`src/trading_framework/research/datasets/predictive_run.py`). That
fingerprint is recorded in the `Lineage` of every `AnalysisResult` (State)
the model produces, alongside the existing `ComponentId` / `ImplementationId`
pair (ADR-MA-002).

**Cost, priced honestly.** Recording the fingerprint is free — it already
exists. The real cost is durable **serialization**: today's `models/fold_*.bin`
joblib blobs are opaque and version-tagged only, with no portability
guarantee across a library upgrade (TD-022, ADR-0023 §7). A promoted model
must load deterministically at inference time for the lifetime it is relied
upon in production State computation, which `joblib` does not guarantee
across a scikit-learn/torch minor version bump. **This ADR does not choose a
replacement format.** A promotion sprint must price a stable serialization
format (or an equivalent re-fit-on-load contract) as its first cost, not
discover it mid-implementation.

**Verification.** A component-identity test asserting the artifact
fingerprint is present and immutable on every `AnalysisResult.Lineage` the
component emits.

### 2. Data leakage (inference-time feature availability)

**Condition.** A model component consumes features exactly like a rule-based
component: through `AnalysisDataView`, subject to the same
`AvailabilityMetadata` and `available_at` enforcement the engine already
applies to every component (ADR-MA-009). Training-time leakage is already
solved — purge and embargo make label-horizon overlap a persisted fold-role
fact, not a training-time courtesy (ADR-0023 §4). The open risk this ADR
must close is different: at **inference** time, nothing today stops a model
component from being wired to a feature whose `available_at` has not yet
elapsed relative to the State's `detected_at`.

**Condition, stated precisely.** Inference-time availability is a
**component-contract** obligation, enforced by the same executor validation
that already rejects a non-causal read for rule-based components (ADR-MA-009
"engine responsibilities"), not a documentation note in the model's spec. A
model component declaring a feature dependency must fail the same way a
rule-based component fails today if the engine cannot prove the feature was
available before the State's timestamp.

**Verification.** A leakage regression fixture (ADR-0023 §4 style
counter-fixture) proving a model component that reads a feature before its
`available_at` is rejected by the executor, not merely by a code-review
convention.

### 3. Feature lineage

**Condition.** Already solved by existing infrastructure — no new mechanism.
A model component declares its feature dependencies as `OutputRef` values,
identically to how a rule-based component declares inputs (`AnalysisResult`
`Lineage`, ADR-MA-005). This keeps the dependency DAG complete and cache
identity correct without a parallel "ML feature" concept.

**Verification.** Existing DAG / lineage contract tests extended with one
model-component fixture; no new test category required.

### 4. Offline/online parity — the hard one

**Condition.** Batch research (Predictive Research training/evaluation) and
the dry-run/live runtime must produce **identical** State values for
identical inputs. This is not automatic: research preprocessing (scaling,
encoding, imputation — fitted per fold, ADR-0023 §4) currently lives in the
research pipeline only. For parity, the **fitted preprocessing transform must
be part of the promoted artifact** and executable, unchanged, on both the
batch research path and the dry-run runtime — the same transform object, not
a re-implementation.

**Minimum acceptance bar.** A parity test on recorded data: replay a fixed
window of historical bars through (a) the batch research prediction path and
(b) the dry-run runtime State path, using the same promoted artifact, and
assert bit-for-bit (or tolerance-bounded, for floating point) identical
predictions. A design sketch for this test is in `S044_GATE.md` §4; this
sprint does not implement the harness or the component, only the sketch.

**Verification.** The parity test above is a **release gate** for any
promotion sprint — it must exist and pass before a model-backed State ships,
not be scheduled as follow-up hardening.

### 5. Model registry

**Condition.** Promotion requires only a **content-addressed artifact
store** — the fingerprint-addressed layout Predictive Research already uses
(`research/predictive_research/runs/{run_id}/`) — not a registry product with
lifecycle state, promotion workflow, or a serving API. TD-021 is restated,
not repaid, by this decision: **no registry is required or implied.** This
must be stated explicitly so a future sprint does not assume registry
infrastructure exists, discover it does not, and build one as an unplanned
prerequisite. IDEA-003 (dedicated feature/model store) stays deferred; this
ADR does not revive it.

**Verification.** N/A — this condition is a negative constraint on scope,
not a testable artifact. A promotion sprint plan that assumes registry
infrastructure fails this ADR's review.

### What is not sufficient for promotion

Strong out-of-sample metrics on a Predictive Research report — a good
baseline delta, stable per-fold performance, acceptable calibration — are a
**precondition** for opening a promotion sprint, never a substitute for the
five conditions above. A promoted model becomes a Market Analysis **input**;
downstream strategies that consume its State must still pass Phase 7
robustness validation like any other Signal Model. Phase 10 research metrics
answer *is there structure?*; Phase 7 answers *does a strategy built on it
survive stress?*. Neither phase's verdict substitutes for the other's.

## Consequences

### Positive

- Every open IDEA-014 question resolves to a concrete, testable condition
  instead of a principle a future sprint would have to reinterpret.
- Reuses existing infrastructure for three of five conditions (lineage,
  training leakage, artifact fingerprint) — a promotion sprint's real new
  work is scoped to serialization, inference-time availability enforcement,
  and the parity harness.
- Explicitly forecloses a registry-product detour (condition 5), which is
  the single most common way this kind of gate gets over-built.
- Downstream robustness stays mandatory, closing the "Phase 10 metrics as a
  verdict" drift risk named in SPRINT_044.md §9.

### Negative

- No serialization format is chosen here; a promotion sprint inherits that
  decision as up-front cost rather than starting with an obvious path.
- The parity test bar is strict (identical values, not "close enough" by
  eyeballing); a genuinely non-deterministic estimator family may not be
  promotable without additional seeding work not scoped here.
- Five conditions across identity, leakage, lineage, parity, and registry
  scope means a promotion sprint touches the executor, the artifact store,
  and the research pipeline in one increment — it will not be small.

## References

- `docs/planning/sprints/S044_GATE.md` — testable conditions expanded into
  entry criteria, plus the parity test design sketch (T013)
- `docs/planning/sprints/S044_WAVE0_DECISIONS.md` — D-S044-12 proposed
  positions this ADR confirms
- `docs/adr/ADR-0023-predictive-research-boundary.md` — leakage policy,
  artifact policy (§4, §7), and the original deferral of this decision
- `docs/adr/ADR-MA-002-component-and-implementation-identity.md` —
  `ComponentId` / `ImplementationId`
- `docs/adr/ADR-MA-005-analysis-result-and-output-identity.md` — `Lineage`,
  `OutputRef`
- `docs/adr/ADR-MA-009-warmup-causality-and-availability.md` —
  `AvailabilityMetadata`, `available_at` enforcement
- `docs/planning/sprints/SPRINT_040.md` §8 — model artifact policy
- `docs/planning/TECHNICAL_DEBT.md` — TD-021 (no model registry), TD-022
  (opaque fitted artifacts)
- `docs/planning/IDEA_INBOX.md` — IDEA-014, IDEA-003 (stays deferred)
- `docs/planning/ROADMAP.md` §13A
