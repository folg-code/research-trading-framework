# ADR-0033 — Predictive Score Delivery Boundary for Strategy Research (16C)

## Status

ACCEPTED

Approved-by: Filip Folga (project maintainer), given directly in
conversation with the orchestrating Claude Code session on 2026-09-08, after
being shown this document's full content (the fingerprint-reference
mechanism, the config-load-time resolution and defense-in-depth family
check, the in-process NumPy evaluation under `available_at`, and Option B /
Option C as the alternatives considered and rejected). The maintainer chose
Option A (in-process evaluation) over Option B (pre-materialized score
column) earlier in the same conversation, before this document was drafted;
this Status update records the separate, explicit acceptance of the
document as written. Answer: "akceptuję".

Date: 2026-09-08
Owners: architecture triage (Claude Code session), for Phase 16 increment
16C, `docs/planning/sprints/SPRINT_058.md`.

## Context

Phase 16 increment 16C ("Signal Quality Scoring",
`docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H.3) requires Strategy
Research to consume a fitted predictive model's score as an ordinary gating
condition — the phase's central vertical slice. Three binding constraints
shape how that can happen:

- **§13H.8 (binding rules for the whole phase):** the simulator owns PnL;
  ML enters simulation *only* through explicit declared strategy semantics,
  *never* by loading model binaries inside Strategy Research; no workflow
  depends on reloading `models/fold_{n}.bin` (TD-022's safe operating
  boundary); no registry appears as a side effect (ADR-0024 condition 5).
- **§13H.3 (16C's own completion criteria):** TD-021 (no model registry) and
  TD-022 (opaque, non-portable fitted blobs) must be repaid *inside* this
  increment, not merely referenced; TD-029 must be explicitly re-deferred to
  16G, in writing and in code, with a config-load-time refusal covered by a
  test. `MODEL_FAMILY_ALLOWLIST` must be unchanged by this increment.
- **§13H.12 Q6 (resolved, Option B):** estimator comparison that may gate a
  strategy is restricted to promotable families (`sklearn.ridge`,
  `sklearn.elastic_net`, `sklearn.logistic`); tree and neural scorers are
  research-only and refused at config load time if declared as a strategy
  gate.

`ADR-0029` (Sprint 049) already built and shipped the mechanism this decision
needs, for a different consumer (the dry-run/live runtime): a promoted
artifact is a content-addressed, framework-owned JSON parameter file
(`research/predictive_research/promoted/{artifact_fingerprint}/artifact.json`),
evaluated by a pure-NumPy closed-form expression living in the **domain
layer** (`research/predictive/`), with no scikit-learn or joblib dependency
at evaluation time. ADR-0029 §9 explicitly anticipated a second consumer:
"the evaluator lives in the domain, not in `infrastructure/ml/`, because
Sprint 050's Market Analysis component must reach it." Promotion
(ADR-0029 §1) already refuses to produce an artifact for a tree or neural
family, with a named error — so no fingerprint under `promoted/` can ever
name a non-promotable family today. ADR-0024 condition 5 forbids any index,
`latest` pointer, status field, or lifecycle field around promoted artifacts;
TD-021's repayment path (§13H.3) is *confirming* a bare fingerprint reference
is usable from a real config consumer, not building an index.

## Decision

Strategy Research consumes a predictive score entirely **in-process, at
simulation time**, through the existing pure-NumPy evaluator ADR-0029
already ships. No new artifact type, no new store, no blob reload.

1. **Reference.** A new strategy condition type (exact name and parameter
   shape is a Sprint 058 task-level decision, not fixed here — see
   Follow-up) is declared in a strategy config and names a promoted artifact
   by its content-addressed `artifact_fingerprint`, the same identity
   ADR-0029 §2 already defines. No index, no alias, no `latest` pointer —
   ADR-0024 condition 5's negative constraint, unchanged.

2. **Resolution — once, at config load time.** The referenced fingerprint is
   resolved via the existing `PromotedArtifactRepository` /
   `PromotedArtifactManifest` / `Ref` types (ADR-0029 §9,
   `research/datasets/`). Resolution is refused **at config load time**, with
   a named error distinguishing two failure modes:
   - no artifact exists at that fingerprint;
   - an artifact exists but its recorded `model_family` is outside
     `MODEL_FAMILY_ALLOWLIST`.
   Because promotion itself already refuses to produce an artifact for a
   non-promotable family (ADR-0029 §1), the second failure mode is
   defense-in-depth, not the primary gate — but it is what turns TD-029's
   re-deferral into a written, tested fact rather than an assumption.

3. **Evaluation — in-process, per occurrence, under `available_at`.** At
   simulation time, for each Signal/Strategy occurrence, the feature snapshot
   Strategy Research already computes under the existing `available_at`
   discipline is passed to the unmodified NumPy evaluator
   (`research/predictive/`) to produce a score (and, for `sklearn.logistic`,
   a probability). The strategy condition compares it to a declared
   threshold. No estimator is fit here — inference only, using the exact
   closed-form expression ADR-0029 §1 already defines and already tests
   against scikit-learn (Comparison 2, Path A).

4. **What this is not.** `infrastructure/ml/`, joblib, and scikit-learn are
   never imported by Strategy Research. `models/fold_{n}.bin` is never
   touched by this path. No new persisted artifact type, index, registry, or
   lifecycle field is introduced.

## Alternatives Considered

### Option B — Pre-materialized score column

Compute scores for a whole dataset/range in a separate batch step ahead of
simulation, persist them as a new artifact type ("score series") with its
own provenance, and have Strategy Research read a plain column — no model
evaluation happens inside Strategy Research's process at all.

- Pros: cleanest process separation; simulation reads a plain data column;
  scoring is auditable independently of any one simulation run; matches
  §13H.3's alternate TD-022-satisfying description ("a materialized score
  column persisted with its own provenance") directly.
- Cons: requires designing and shipping a new persisted-artifact contract
  (schema, provenance fields, a batch materialization step, a join-under-
  `available_at` mechanism distinct from the one Strategy Research already
  has) inside a sprint whose scope is explicitly kept narrow; duplicates
  machinery ADR-0029 already built and proved; widens 16C past "the vertical
  slice" into artifact-design work more naturally suited to 16D or a later
  increment.
- Reason rejected (maintainer decision, 2026-09-08): no demonstrated need for
  the added artifact-design cost this sprint — the pure-NumPy evaluator is
  cheap per occurrence (a closed-form dot product), and `signal_occurrences`
  samples (16B) are already a bounded, filtered row set, not a full-bar-series
  computation. Rejected for this increment, not forever — see Follow-up.

### Option C — In-process reload of the fitted library blob

Load `models/fold_{n}.bin` (joblib/sklearn) directly inside Strategy
Research at simulation time.

- Pros: none beyond "the pattern already exists elsewhere in research code."
- Cons: violates §13H.8's binding rule that ML enters simulation only through
  declared strategy semantics, never by loading model binaries; pulls
  scikit-learn into a path that today has no such dependency; reopens the
  coupling ADR-0029 §7 narrowly and deliberately declined to grant ("NOT
  GRANTED: any general 'blobs are loadable now' capability").
- Reason rejected: forbidden by this phase's own binding rules and by
  ADR-0023 §7 / ADR-0029's narrow amendment.

## Consequences

### Positive

- Zero new dependencies, zero new artifact types, zero new persisted-data
  contracts. 16C stays the narrow vertical slice §13H.3 requires.
- TD-021 is repaid exactly as prescribed: a real, non-Predictive-Research
  consumer (a Strategy Research config) uses the bare content-addressed
  fingerprint successfully, with no index built.
- TD-022's promotion branch is repaid: the score path depends on
  `artifact.json` only, never on `models/fold_{n}.bin` — provable by a test
  (no `infrastructure/ml` import from Strategy Research's condition module).
- TD-029 is repaid by construction plus one explicit, tested defense-in-depth
  check, rather than by a fragile convention.
- Reuses ADR-0029's evaluator, which is already parity-tested against
  scikit-learn (Path A) — 16C does not need to re-prove numerical
  correctness, only the new call site.

### Negative

- Strategy Research's simulation loop gains a new per-occurrence NumPy
  evaluation cost. Expected to be small (a closed-form dot product over a
  bounded feature vector) but not zero, and not benchmarked by this ADR.
- Strategy Research's condition layer gains a direct (read-only) dependency
  on `research/predictive/` and `research/datasets/`'s promoted-artifact
  types — a new, narrow cross-module edge that did not exist before. It must
  be added to the module boundary allow-list, its direction (Strategy
  Research depends on Predictive Research's promoted-artifact contract,
  never the reverse) asserted by a boundary test, consistent with existing
  practice (ADR-0022, ADR-0026 Amendment 1).
- A strategy config now names a specific promoted artifact fingerprint
  directly — reproducibility of a strategy run therefore also depends on
  that promoted artifact continuing to exist on disk (unchanged from how
  promoted artifacts already work; not a new risk, but now inherited by
  Strategy Research configs too).

### Neutral / Trade-offs

- This is an inference-only path: no estimator is ever fit inside Strategy
  Research, at any point. The simulator still owns every fill, slippage,
  sizing, and ledger decision, unchanged.
- Option B is not eliminated by this ADR — it remains available as a later,
  explicitly-scoped increment if the trigger in Follow-up fires.

## Follow-up

- If per-occurrence NumPy evaluation is measured (16C's worked example, or
  later use) to be a real performance bottleneck, or if independent
  auditability of scores becomes a stated need, revisit Option B as its own,
  explicitly scoped follow-up — not silently folded into 16C.
- The exact strategy-condition name and parameter surface (single threshold
  vs. banded thresholds, class-probability vs. regression score handling) is
  a Sprint 058 task-level decision, not fixed by this ADR.
- 16G's tree/neural serialization ADR (§13H.9 row 3) is a separate, later
  decision. Nothing here pre-decides it; if 16G's mechanism ever makes
  tree/neural artifacts promotable, this ADR's decision (fingerprint
  reference + in-process NumPy evaluation) is expected to extend to them
  without a rewrite — the evaluator would need a family-specific closed-form
  expression, which is 16G's scope, not this ADR's.

## Related

- `docs/adr/ADR-0023-predictive-research-boundary.md` §7 — the narrow
  blob-reload exception this decision does not widen.
- `docs/adr/ADR-0024-machine-learned-state-promotion.md` — condition 5 (no
  registry), consumed unchanged.
- `docs/adr/ADR-0029-promoted-predictive-artifact.md` — the evaluator and
  promotion store this decision reuses verbatim; §9 anticipated this exact
  kind of second consumer.
- `docs/adr/ADR-0031-predictive-sample-spec-and-task.md` — `SIGNAL_QUALITY`
  `PredictiveTask` and `signal_occurrences` samples 16C's study is built on.
- `docs/adr/ADR-0032-predictive-run-verdict-artifact.md` — the verdict 16C's
  worked-example run will also carry.
- `docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H.3, §13H.8,
  §13H.9 (row 2), §13H.12 Q6 — the binding scope and rules this decision
  satisfies.
- `docs/planning/TECHNICAL_DEBT.md` — TD-021, TD-022, TD-029.
- `docs/planning/sprints/SPRINT_058.md` — the sprint this ADR is authored
  for.
