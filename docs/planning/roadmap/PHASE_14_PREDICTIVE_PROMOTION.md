# Phase 14 — Predictive Model Promotion

```text
Status: APPROVED (maintainer, 2026-09-02) — 14A COMPLETE, 14B NOT planned
```

Full detail for `ROADMAP.md` §13F — this is the LIVE, canonically-updated location for this
phase; `ROADMAP.md` carries only a short pointer stub under the same section number.

**This file is expected to keep changing** as the phase progresses (Wave 0 decisions, sprint
openings, status flips). Unlike `docs/planning/ROADMAP_COMPLETED_PHASES.md` — which is
frozen history — edits to this phase's detail happen **HERE**, not by re-inflating the
`ROADMAP.md` stub.

Internal heading numbering is preserved exactly as it was in `ROADMAP.md`, so a citation of
the form `roadmap/PHASE_14_PREDICTIVE_PROMOTION.md §13F` resolves, matching the convention
already used in `ROADMAP_COMPLETED_PHASES.md`.

---

# 13F. Phase 14 — Predictive Model Promotion (APPROVED)

**Status:** **APPROVED** (maintainer, 2026-09-02). **Sprint 049 (increment
14A) is COMPLETE** (15/15, on `sprint/promotable-predictive-artifact`; final
integration PR to `main` pending) — ADR-0024 conditions 1 and 5 closed,
condition 4's offline half (Path A) built and passing at its locked bars
(measured maximum `y_proba` deviation: `0.0`). **Sprint 050 (increment 14B)
is NOT planned yet.** Phase 14 as a whole is **NOT complete** — 14A ships no
Market Analysis component, no State, no executor change, and no dry-run
session; see `docs/planning/sprints/SPRINT_049.md` §13 Review.
**Product source:** `docs/product/PRD-ml-signal-promotion.md` — the maintainer's
discovery record; authoritative on scope, format, fold selection and the parity
bar.
**ADRs:** ADR-0024 (promotion conditions) — ACCEPTED, the binding input.
**ADR-0029** (promoted artifact parameter format, promotion store, parity bars,
and the narrow ADR-0023 §7 amendment) — **ACCEPTED 2026-09-02**. ADR-0030
(inference-time availability enforcement) — the S049-T001 finding concluded
the mechanism ADR-0024 condition 2 presupposes does not exist in the executor
today; ADR-0030 is needed and sizes Sprint 050.
**Gate:** `docs/planning/sprints/S044_GATE.md` — entry criteria and the parity
test design sketch (§4).

## Purpose

Close the gap Phase 10 deliberately left open: a trained predictive model can be
evaluated offline, but nothing trained is reachable from a strategy. Phase 14
makes a trained model produce a Market Analysis **State**, consumed by a Signal
Model exactly like a rule-based component, all the way into the **BTC futures
dry-run runtime** (the existing Phase 8A infrastructure, Sprints 019–024) — under
ADR-0024's five conditions, none of them waived.

This is the phase ADR-0024 was written to gate. Its own Consequences section
says it "will not be small."

## v1 scope, locked by the PRD and ADR-0029

```text
IN    one instrument (BTC futures), one horizon
IN    LINEAR AND LOGISTIC model families only
IN    a framework-owned NumPy parameter format — ZERO ML dependency in the
      dry-run/live runtime image
IN    exact offline/online parity as a RELEASE GATE, not a follow-up
IN    dry-run only, composed via strategy_file (ADR-0027) with Phase 13's
      BracketExitModel / EquityPercentRiskModel (ADR-0028)

OUT   real-money trading; multi-instrument / cross-asset; auto-retraining or
      online learning; a model registry or promotion UI; tree (xgboost /
      lightgbm / catboost) and neural (torch) families; ONNX or any
      cross-library exchange format
```

Tree/neural promotion is **deferred, not rejected** — it needs the
version-pinned joblib path that v1 declines to build. It becomes a candidate
follow-on track once this mechanism is proven end to end.

## Two increments, deliberately sequenced

```text
14A — Promotable Predictive Artifact          Sprint 049 (COMPLETE, 15/15)
      ADR-0024 conditions 1 and 5 closed; condition 4's OFFLINE half (Path A)
      built and passing (measured maximum y_proba deviation: 0.0). Touches
      the research pipeline and storage only. Ships NO Market Analysis
      component, NO executor change, NO State.

14B — Model-Backed Market Analysis State      Sprint 050 (NOT planned yet)
      ADR-0024 conditions 2, 3 and condition 4's RUNTIME half (Path B) closed.
      The model component, the registry-injection seam in the dry-run runtime,
      and the parity harness as a RELEASE GATE. Touches market_analysis/
      execution and execution/runtime. Ends in a 3-5 day BTC dry-run session.
```

Sprint 050 is **not** planned in the same pass as Sprint 049. The reasoning was
re-checked after the PRD narrowed v1, and one original reason is now spent:

- ~~its design depends on the serialization format, which is unknown~~ —
  **closed** by ADR-0029; Sprint 050's deployment footprint is now known to be
  *zero extras*.
- ~~its design depends on the S049-T001 finding — whether the executor
  mechanism ADR-0024 condition 2 presupposes actually exists~~ — **closed**:
  S049-T001 concluded the mechanism does not exist, and ADR-0030 will be
  needed. Sprint 050 must include writing and getting that ADR approved.
- **still standing:** whether Path A holds at its locked bars is not yet known
  (Sprint 049 Wave 3 work).
- **added:** conditions 2 and 3 and the online half of condition 4 are
  executor/runtime work whose cost is **independent of the serialization
  format**. The format choice shrank Sprint 050's deployment concerns to
  nothing; it did not shrink its executor concerns at all. That is the structural
  reason the split survives the narrower scope.

## Primary flow (the phase's end state, reached only after 14B)

```text
PredictiveRunEnvelope (Phase 10), LAST walk-forward fold
        ↓  promote_predictive_run  (one-time blob read, ml extra)     [14A]
research/predictive_research/promoted/{artifact_fingerprint}/
        manifest.json  +  artifact.json  (weights + intercept + fitted
        preprocessing statistics, as PLAIN NUMBERS, as one unit)
        ↓  load, format/family-guarded, evaluated by PURE NUMPY       [14A]
Path A: re-predict the run's TEST rows vs predictions.parquet         [14A]
        exact for linear; y_proba for logistic within atol=1e-15
        ↓
Market Analysis STATE component; artifact_fingerprint as a STR        [14B]
        parameter → CanonicalParameters → Lineage → cache identity
        ↓  features read through AnalysisDataView, available_at enforced
Path B: dry-run runtime State values == research values, EXACTLY      [14B]
        ↓
Signal Model consumes the State exactly like a rule-based one,        [14B]
        composed via strategy_file with a Bracket exit and equity sizing
        ↓
Phase 7 robustness on the resulting strategy — MANDATORY, never skipped
        (must account for TD-027: delay stress rejects bracket exits)
```

## Expected capabilities

- a `promote_predictive_run` workflow turning a Phase 10 run's **last fold** into
  a single, content-addressed, deterministically loadable **parameter file**
  whose **fitted preprocessing statistics travel inside it** as one unit with the
  estimator parameters,
- a pure-NumPy evaluator for that file, living in the domain layer and requiring
  **no optional extra** — so the dry-run/live image is unchanged,
- a load-time format and model-family guard with no bypass, plus a
  promotion-time library-version guard for the one blob read,
- a Market Analysis State component backed by that artifact, identified in
  `Lineage` by the artifact fingerprint and declaring its features as
  `OutputRef` values like any rule-based component,
- executor-enforced inference-time feature availability for model components
  (per ADR-0030, needed per the S049-T001 finding),
- a parity harness proving batch research and the dry-run runtime produce
  **identical** State values from the same artifact — running in **default CI**,
  because there is no ML dependency to gate it behind.

## Binding rules

```text
ADR-0024's five conditions are inherited whole; none is waived by this phase
Condition 5 is a NEGATIVE constraint: no model registry, no lifecycle state, no
    serving API. A plan that starts building one has misread the ADR.
Condition 4's bar is EXACT EQUALITY for the offline/online comparison (the
    release gate). The single ulp-bounded tolerance ADR-0029 §6 permits applies
    ONLY to the Sprint 049 sklearn cross-check's y_proba column, and is NOT
    inherited by the release gate.
ADR-0023 §4 (purge, embargo, dataset fingerprint) is NOT reopened
ADR-0023 §7 is amended NARROWLY by ADR-0029 — one workflow, one read, one
    purpose; research-run blobs stay non-reloadable by everything else
Strong Phase 10 metrics are a PRECONDITION for promotion, never a verdict that
    the model should trade (ADR-0024, "What is not sufficient for promotion")
ml / ml-trees / dl remain out of the default install and default CI — and, per
    ADR-0029, out of the RUNTIME IMAGE entirely. Promotion needs `ml`;
    inference needs nothing.
No new dependency of any kind: the parameter format needs only NumPy, already
    a default-install dependency
Phase 13's Exit/Risk work (ADR-0028) is CONSUMED, never modified
```

## Completion criteria

- a trained **linear or logistic** model, promoted through a content-addressed
  artifact store with no registry, produces a Market Analysis State consumed by a
  Signal Model,
- the artifact fingerprint appears on every `AnalysisResult.Lineage` the model
  component emits (condition 1),
- a leakage counter-fixture proves the **executor** — not a code-review
  convention — rejects a model component reading a feature before its
  `available_at` (condition 2),
- the model component declares its features as `OutputRef` values, covered by
  the existing DAG/lineage tests plus one model-component fixture (condition 3),
- the **parity harness passes as a release gate**: batch research and the
  dry-run runtime produce **exactly identical** State values for identical
  inputs, from the same promoted artifact including its fitted preprocessing
  (condition 4, PRD success metric 1),
- a **BTC futures dry-run session runs 3–5 consecutive days** on a promoted
  model with no divergence from an offline re-run over the same recorded window
  (PRD success metric 2),
- a named downstream Signal Model has a Phase 7 robustness plan and it is
  executed, not skipped (S044_GATE §1.5, PRD success metric 3),
- no registry, lifecycle state, or serving API exists anywhere in the delivery
  (condition 5).

## Dependencies

- Phase 10 complete (Sprints 039–044) — **satisfied**,
- ADR-0024 and `S044_GATE.md` on `main` — **satisfied** (#348),
- ADR-0029 — **ACCEPTED** (2026-09-02); on the sprint branch,
- Phase 12's `strategy_file` loader (ADR-0027) and Phase 13's Exit/Risk models
  (ADR-0028) — **satisfied** (merged #366, #368–#383); consumed by 14B's dry-run
  composition, not modified,
- **a real (non-synthetic) trained candidate model showing genuine out-of-sample
  structure on BTC data** — **does not exist**; Phase 10's validated results are
  on synthetic known-signal fixtures (ADR-0023 §8). Tracked as a prerequisite
  **outside** Sprint 049 (no 14A task depends on it); it gates 14B and the PRD's
  success metrics 2 and 3. **Now being actively pursued by Phase 15 (§13G,
  Sprints 051+052)** — closes this dependency only on a positive result,
- **a named downstream robustness plan** (S044_GATE §1.5) — **does not exist**;
  same status: prerequisite outside Sprint 049, gates 14B,
- **ADR-0030** (inference-time availability enforcement) — needed per
  S049-T001's finding; must be written and approved before 14B implementation.

## Main risks

- **Exact parity may not survive contact with two implementations.** The release
  gate (offline NumPy == online NumPy) is structurally exact — same code, same
  artifact. But Sprint 049's Path A compares the NumPy evaluator against
  **sklearn's** own recorded predictions, and sklearn's logistic `predict_proba`
  uses `scipy.special.expit` rather than a NumPy sigmoid. The maintainer chose to
  keep both families with a bounded `atol=1e-15` on that one column rather than
  drop logistic (ADR-0029 §6, Q7). This is the maintainer's named riskiest
  assumption meeting its first real test, deliberately in 14A rather than 14B.
- **Condition 2 is larger than ADR-0024 priced it — confirmed, not just risked.**
  S049-T001 verified line-by-line that the executor does not enforce
  inference-time `available_at` rejection today (`executor.py`, `planner.py`,
  `assembler.py` all checked; no such mechanism exists). ADR-0030 is required
  before 14B can close condition 2.
- **The framework now owns a `predict` implementation** that must stay in step
  with scikit-learn's; only the Path A cross-check detects drift.
- **The linear/logistic restriction may bind sooner than expected** — the first
  real BTC candidate model that shows structure may well be a tree model, in
  which case the operator hits a refusal and the deferred joblib path becomes the
  next increment rather than a distant one.
- **TD-027 constrains 14B's robustness plan:** the Robustness delay stress still
  rejects bracket exits (§13E). If the promoted-model strategy uses
  `BracketExitModel`, not every stress dimension is available, and the S044_GATE
  §1.5 plan must say so rather than assume a full stress suite.
- **Promotion drifting into a registry by accretion** — an index file, then a
  `latest` pointer, then a status field. Guarded as an acceptance criterion with
  a test, not as a principle in prose.
- **A synthetic-fixture model mistaken for a tradeable one.** If 14B promotes one
  as plumbing, that must be stated loudly, not left implicit.

## Out of scope

- real-money trading; multi-instrument or cross-asset portfolios; auto-retraining,
  online learning, drift detection, or any automatic re-promotion (PRD Non-goals),
- tree and neural model families, and the version-pinned joblib format they
  require — **deferred to a later increment**, not rejected,
- ONNX or any cross-library exchange format — rejected for v1 because a second
  numerical implementation threatens the exact-match bar,
- a model registry, model lifecycle states, a promotion workflow product, or a
  serving API (ADR-0024 condition 5; TD-021 restated, not repaid),
- IDEA-003 (a dedicated feature/model store) — stays deferred,
- **any change to Phase 13's Exit/Risk models, the bracket kernel, or the
  simulator** — this phase consumes them,
- new estimator families, new predictive features, cross-sectional studies, or
  SHAP — extending Predictive Research itself is a separate track, sequenced
  **after** this phase at the maintainer's stated direction (PRD preamble:
  research expansion is the explicit next priority; report expansion is third),
- report/dashboard extensions for promoted models — likewise a later track,
- any claim that a promoted State is a validated trading edge — that is Phase 7
  robustness's answer, and it is never substituted by Phase 10 metrics.
