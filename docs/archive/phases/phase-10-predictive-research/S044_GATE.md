# Sprint 044 Gate — IDEA-014 Promotion

Binding entry criteria for **any future sprint implementing IDEA-014**
(promoting a trained model to a Market Analysis State). Written as S044-T011,
alongside `ADR-0024-machine-learned-state-promotion.md` (S044-T012). Date:
2026-08-28.

Sprint 044 does **not** implement IDEA-014. This document, together with
ADR-0024, is what a maintainer checks before opening that sprint. It is
**not** the Sprint 044 task board — Wave 0 lives in `SPRINT_044.md` and
`S044_WAVE0_DECISIONS.md`.

---

## 1. Entry: an IDEA-014 implementation sprint may start

All of the following must hold:

1. `ADR-0024-machine-learned-state-promotion.md` is on `main`.
2. This gate document is on `main`.
3. Every condition in §2 below has a concrete, funded plan in the candidate
   sprint's Wave 0 — not a restatement of "we'll figure it out."
4. The candidate Predictive Research run being promoted has a Phase 10
   report (Sprint 041 HTML report) showing a baseline delta above the
   permutation baseline on every fold, not just pooled (D-S044-07 sort
   discipline extends to promotion review).
5. A named downstream Signal Model / Strategy Research plan exists for
   *validating* the promoted State through Phase 7 robustness — promotion
   without a robustness plan is out of scope for the sprint that promotes.

**Decision:** none of the five conditions in §2 are satisfied today. This
gate is not yet open. It exists so the next attempt starts from testable
conditions instead of re-litigating IDEA-014's five questions from scratch.

---

## 2. The five conditions (from ADR-0024)

Each row is copied from ADR-0024 §Decision as a checklist; ADR-0024 is the
source of truth if this table and the ADR ever disagree.

| # | Condition | Verification | Status at this gate |
|---|-----------|---------------|----------------------|
| 1 | Artifact identified by a fingerprint (dataset + spec + seed + library versions), recorded in every State's `Lineage` | Component-identity test on `AnalysisResult.Lineage` | Fingerprint exists (`run_fingerprint`); serialization format **not chosen** |
| 2 | Inference-time feature availability enforced by the component contract (`available_at`), not convention | Leakage regression fixture rejecting a component reading an unavailable feature | Training-time leakage solved (S039); inference-time enforcement **not built** |
| 3 | Feature dependencies declared as `OutputRef`, same as rule-based components | Existing DAG/lineage tests + one model-component fixture | Already solved (S039); no new work |
| 4 | Batch research and dry-run runtime produce identical State values for identical inputs (preprocessing travels with the artifact) | Parity test on recorded data (§4 sketch) | **Not built** — hardest open item |
| 5 | Promotion needs only a content-addressed artifact store, no registry product | N/A — negative constraint on scope | Already true (fingerprint-addressed run storage); must stay explicit |

**Reading this table:** conditions 3 and, partially, 1 and 5 are already
satisfied by Phase 10 infrastructure. Conditions 2 and 4 are genuine new
implementation work — a promotion sprint's Wave 0 must price them, not
assume them.

---

## 3. What promotion is not

- **Not** a verdict that the model should trade. Phase 10 answers *is there
  predictable structure?*; a promoted State is a Market Analysis input, and
  any strategy consuming it still needs a Phase 7 robustness pass, exactly
  as if it depended on a rule-based State (ADR-0024, "What is not
  sufficient for promotion").
- **Not** a registry product. A promotion sprint that starts by designing
  model lifecycle states, a serving API, or promotion workflow tooling has
  misread condition 5 — see ADR-0024 §5 and TD-021.
- **Not** an excuse to relax the extras boundary. `apps/dashboard` still
  must not import `trading_framework` or install `ml` / `ml-trees` / `dl`
  extras (ADR-0022; unchanged by this gate). A promoted model runs inside
  `trading_framework`'s execution/runtime boundary, not the dashboard.
- **Not** blanket authorization to reopen ADR-0023's leakage or artifact
  policy. Training-time purge/embargo, dataset fingerprinting, and the
  "durable facts are predictions + metrics" rule (ADR-0023 §4, §7) are
  inherited locks, restated here, not reopened.

---

## 4. Parity test design sketch (S044-T013)

This is a **sketch**, not an implementation. It exists so condition 4 has a
concrete shape a promotion sprint can build against, rather than discovering
the test design mid-sprint.

### 4.1 What it proves

For a fixed historical window and a fixed promoted artifact, the batch
research prediction path and the dry-run runtime State path produce the
same output for the same input bars.

### 4.2 Sketch

```text
Fixture:
  - a small, fixed set of historical bars (synthetic, CI-safe — same
    discipline as D-S039-CI-dataset; no NQ dependency)
  - one promoted artifact: fitted estimator + fitted preprocessing
    transform, addressed by its run_fingerprint

Path A — batch research replay:
  1. Load the fixture bars into the same feature-matrix builder Predictive
     Research uses (declared OutputRef features, S039 dataset builder).
  2. Apply the artifact's fitted preprocessing transform.
  3. Run the fitted estimator; record predictions keyed by (entity_id,
     as-of timestamp).

Path B — dry-run runtime replay:
  1. Feed the same fixture bars through the dry-run runtime's Market
     Analysis execution path (ADR-MA-009 availability-enforced reads).
  2. The promoted model component consumes the same declared OutputRef
     features through AnalysisDataView.
  3. Apply the *same* fitted preprocessing transform object loaded from
     the artifact (not a re-implementation) inside the component.
  4. The component emits a State AnalysisResult; record its value keyed
     by (entity_id, as-of timestamp).

Assertion:
  For every (entity_id, timestamp) pair present in both paths, Path A's
  prediction and Path B's State value are equal within a declared
  floating-point tolerance (exact equality is the target; a tolerance is
  a documented compromise, not a default).

Failure handling:
  A mismatch is a parity defect, not a flaky test — same posture as
  ADR-0023 §4's leakage counter-fixtures: stop and report, do not loosen
  the tolerance to make it pass.
```

### 4.3 What the sketch deliberately leaves open

- Which historical window and how many bars — sized by the promotion
  sprint against its actual promoted model, not fixed here.
- The floating-point tolerance value — a promotion sprint chooses it and
  justifies the choice; this sketch does not pre-select one.
- Whether the dry-run runtime needs new plumbing to load a fitted artifact
  at all (it likely does — this sketch assumes that plumbing exists by the
  time this test runs, not that it is free).

---

## 5. References

- `docs/adr/ADR-0024-machine-learned-state-promotion.md` — binding decision
  this gate operationalizes
- `docs/adr/ADR-0023-predictive-research-boundary.md` §4, §7 — inherited
  leakage and artifact-policy locks
- `docs/adr/ADR-0022-repository-top-level-layout.md` — apps boundary,
  unaffected by this gate
- `docs/adr/ADR-MA-002-component-and-implementation-identity.md`
- `docs/adr/ADR-MA-005-analysis-result-and-output-identity.md`
- `docs/adr/ADR-MA-009-warmup-causality-and-availability.md`
- `docs/planning/sprints/SPRINT_044.md` §5 — the five IDEA-014 questions as
  originally posed
- `docs/planning/sprints/S044_WAVE0_DECISIONS.md` D-S044-12 — proposed
  positions this gate and ADR-0024 confirm
- `docs/planning/sprints/SPRINT_040.md` §8 — model artifact policy
- `docs/planning/TECHNICAL_DEBT.md` — TD-021, TD-022
- `docs/planning/IDEA_INBOX.md` — IDEA-014 (status updated separately in
  S044-T015, Wave 4 — this gate does not change IDEA_INBOX.md)
