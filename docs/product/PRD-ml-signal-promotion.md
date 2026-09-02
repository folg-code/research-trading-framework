# PRD — Machine-Learned Signal Promotion to Runtime (ADR-0024 promotion sprint)

Feature-level PRD within the existing Trading Research Framework product,
following the grill-me discovery pattern established for Phase 2F/11 and
Custom Strategy Authoring (`docs/product/PRD-strategy-authoring.md`). This
PRD covers the largest of three ML/AI directions the maintainer named
(promotion to runtime; research expansion; report expansion), sequenced
first because it has the biggest architectural footprint. Research
expansion is the explicit next priority after this ships; report expansion
is third.

Note on sequencing: an `architect` pass (Sprint 049 — "Promotable Predictive
Artifact", Phase 14A) already produced a candidate plan before this PRD was
written down, because the maintainer asked to explore the space first. This
PRD is the retroactive discovery record; where it conflicts with
`SPRINT_049.md` / `S049_WAVE0_DECISIONS.md`, this PRD's decisions (made
directly with the maintainer) win, and those sprint documents must be
reconciled against it before implementation starts.

Numbering note: an earlier draft of this PRD and its sprint documents used
"Sprint 048 / Phase 13A" — those numbers were taken by real merged work
(Sprint 048 = Exit/Risk Model Expansion and Catalog Growth, Phase 13,
ROADMAP §13E). The promotion work is **Sprint 049 / Phase 14A** (ROADMAP
§13F), and its runtime successor is **Sprint 050 / Phase 14B**.

## Problem

Phase 10 (Sprints 039–044) built a complete offline Predictive Research
methodology: declared feature matrices with `OutputRef` lineage, purged and
embargoed walk-forward splitting, sklearn/tree/neural estimators, and a
read-only report. None of it reaches a trading decision. A trained model's
predictions live only in `research/predictive_research/runs/{run_id}/` —
they are never consumed by a `SignalModelDefinition`, never evaluated by
`BarSequentialSimulator`, and never seen by the dry-run/live runtime.
ADR-0023 §1 states this as a deliberate boundary ("a trained model is never
promoted to a tradable signal inside Phase 10") and ADR-0024 names five
conditions that must hold before that boundary can be crossed, without
implementing any of them.

The maintainer wants to actually cross it: a model trained and evaluated in
Predictive Research should be able to drive a real BTC futures dry-run
session (Phase 8A's existing live infrastructure), composed into a strategy
exactly the way a rule-based Signal Model is today (Market × Signal × Exit ×
Risk, ADR-0016; loadable via `strategy_file`, ADR-0027).

## Goals (v1)

- **A promoted model produces a Market Analysis State/Signal consumed like
  any rule-based component** — same `AnalysisDataView` read path, same
  `AvailabilityMetadata`/`available_at` enforcement (ADR-MA-009), same
  `OutputRef`/`Lineage` machinery. No parallel "ML feature" concept.
- **Offline/online parity is a release gate, not a follow-up.** A promoted
  artifact must produce identical (exact, not tolerance-bounded — see
  Success metrics) predictions when re-evaluated through the batch research
  path and through the dry-run runtime path, for the same historical
  window, before it may run live.
- **Scope is deliberately narrow: one instrument, one horizon, linear/
  logistic models only, for v1.** BTC futures, reusing the existing Phase
  8A dry-run infrastructure (Sprint 019–024) rather than building a new data
  path. Tree/neural families are an explicit non-goal until this mechanism
  is proven (see Non-goals).
- **Serialization: framework-owned parameter format, not a fitted-library
  blob, for v1.** The promoted artifact is a plain parameter file (weights,
  intercept, and the fitted preprocessing statistics already exposed by
  `FittedSklearnPreprocessor.statistics()`) evaluated by pure NumPy in both
  the research and runtime paths — no scikit-learn/XGBoost/torch dependency
  enters the dry-run/live runtime image, and the parity test runs in default
  CI, not a gated `ml` job. A version-pinned joblib/pickle format for tree
  and neural families is explicitly deferred to a later iteration once this
  narrower mechanism is proven end-to-end.
- **Promoted artifact = the last walk-forward fold**, trained on the most
  recent available TRAIN span. This is the operator's intuitive default;
  it is a v1 choice, not a claim that it is optimal (see Open questions for
  the deferred alternative).
- **Operator-facing surface matches the existing CLI conventions**
  (ADR-0026, ADR-0027): promoting and running a model-backed strategy should
  feel like the existing `strategy_file` flow, not a bespoke ML-only path.

## Non-goals (v1)

- **Live trading with real money.** v1 stops at dry-run. Connecting a
  promoted model to real execution is a separate, later decision.
- **Multi-instrument / cross-asset portfolios.** One instrument, one
  horizon, matching the existing Predictive Research first-slice limit
  (ADR-0023 §9). No aggregation of multiple ML signals in v1.
- **Auto-retraining or online learning.** Promotion is a manual,
  operator-triggered act on an already-completed Predictive Research run.
  The runtime never retrains or fine-tunes.
- **A model registry or promotion-management UI.** ADR-0024 condition 5
  already forecloses this — content-addressed artifact storage only.
- **Tree-based (XGBoost/LightGBM/CatBoost) or neural (Sprint 043) model
  families.** These require the version-pinned joblib path deferred above;
  v1 proves the mechanism on linear/logistic models only.
- **A stable cross-library exchange format (ONNX) for v1.** Considered and
  rejected for the first slice: it would introduce a second numerical
  implementation of the model, which directly threatens the exact-match
  parity bar this PRD requires as a release gate. Revisit only if the
  framework-owned parameter format proves too narrow for future model
  families.

## Success metrics

1. **Parity test passes in default CI.** Given a promoted linear/logistic
   artifact and a fixed recorded window of historical bars, the batch
   research prediction path and the dry-run runtime State path produce
   **exactly equal** predictions (floating-point exact, given the
   NumPy-only evaluation choice above) — not "close enough." This test is a
   release gate: it must exist and pass before any model-backed State can
   run in dry-run.
2. **A real BTC futures dry-run session runs for 3–5 consecutive days**
   using a promoted model as its Signal Model, composed via `strategy_file`
   (ADR-0027) with an Exit/Risk model, on the existing Phase 8A dry-run
   infrastructure, with no divergence between the predictions the runtime
   produced and what the same artifact would produce if re-run offline
   against the same recorded window.
3. **Downstream robustness is not skipped.** A strategy built on the
   promoted Signal still goes through Phase 7 robustness validation before
   its 3–5 day dry-run is treated as meaningful evidence — Phase 10/14
   research metrics answer "is there structure?"; Phase 7 answers "does a
   strategy built on it survive stress?" (ADR-0024, "What is not sufficient
   for promotion").

## Riskiest assumption

**That offline (batch research) and online (dry-run runtime) evaluation of
the same promoted artifact can be made to agree exactly, not approximately.**
The maintainer named this directly: "Wyniki w backtestach muszą pokrywać się
z dry-runem. Jeśli tak nie będzie to wywraca plan." If floating-point
evaluation order, Polars vs. runtime data representations, or fitted
preprocessing statistics diverge between the two paths, ADR-0024 condition 4
cannot be satisfied as stated and the whole promotion mechanism needs
re-scoping (e.g. a tolerance-bounded bar instead of exact match) before any
further work is meaningful. This is why the framework-owned NumPy parameter
format (not a fitted-library blob, not ONNX) was chosen for v1: it minimizes
the surface area where such a divergence could hide, at the cost of
supporting linear/logistic models only.

Two supporting risks, surfaced by the architect's Sprint 049 pass and worth
recording here rather than losing them:

- The executor may not actually have a per-feature `available_at`
  rejection mechanism today (ADR-MA-009's stated engine responsibilities
  are warm-up extension and output-range validation, not inference-time
  per-read enforcement) — ADR-0024 condition 2 may require executor-wide
  work, not a narrow "wire the component in" change. This must be spiked
  and confirmed before Sprint 050 (the runtime-integration sprint) is
  sized.
- ADR-0023 §7 ("no workflow may depend on reloading a fitted blob") is an
  ACCEPTED decision this PRD's promotion mechanism necessarily narrows.
  That narrowing must be a deliberate ADR amendment (research run blobs
  stay opaque and non-reloadable; only a separately produced, separately
  fingerprinted promoted artifact is loadable) — not a silent contradiction.
  Recorded as ADR-0029 §7.

## Constraints

- No hard deadline. Correctness over speed.
- Target instrument: BTC futures, reusing the existing Phase 8A live
  dry-run infrastructure (Sprint 019–024) rather than building a new data
  path.
- Every ADR and Wave 0 decision set goes back to the maintainer for explicit
  review before implementation starts — no self-certified approval records
  (per the precedent already set in ADR-0024's own Approved-by section).

## User story

As an operator, once a Predictive Research run has completed and its
metrics look sound, I promote its last-fold linear/logistic model to a
named artifact. I then reference that artifact from a `strategy_file`
(ADR-0027) as the Signal half of a Market × Signal × Exit × Risk
composition, and run `trading-cli dry-run start` against BTC futures. The
model produces Signals through the same executor path a rule-based
component would, subject to the same availability enforcement. Before I'm
allowed to do this at all, a parity test has already proven — in CI — that
this exact artifact predicts identically offline and online.

## Open questions

All five forks below were **answered by the maintainer on 2026-09-02** and are
recorded in ADR-0029 (ACCEPTED) and `S049_WAVE0_DECISIONS.md`. They are kept
here as the discovery record, with their answers noted.

- **Re-fit vs. re-serialize at promotion time.** ANSWERED: **extract from the
  existing fitted blob**, a one-time promotion-time read, no re-fit — so the
  promoted artifact is numerically the same model that produced the run's own
  reported metrics (ADR-0029 §4).
- **CLI surface for promotion.** ANSWERED: **`trading-cli research promote`**,
  a subcommand of the existing `research` group (ADR-0029 §8).
- **A real (non-synthetic) candidate model.** STILL OPEN. Phase 10's validated
  results are on synthetic known-signal CI fixtures (ADR-0023 §8,
  D-S039-CI-dataset). This PRD's success metrics assume a model trained on real
  BTC market data exists and shows genuine out-of-sample structure before
  promotion is attempted — that model does not exist yet and building
  confidence in one is implicitly prerequisite work, not covered by this PRD.
  It is a **prerequisite tracked outside Sprint 049**, blocking Sprint 050 and
  success metrics 2 and 3, not any Sprint 049 task.
- **Named robustness plan for the promoted-model strategy** (S044_GATE.md
  §1.4/§1.5 are unsatisfied today) — STILL OPEN, same status: gates the dry-run
  success metric above, not the parity test.
- **Executor availability-enforcement spike outcome** — may resize or
  re-split the runtime-integration sprint (**Sprint 050**, Phase 14B) once
  answered. The spike is S049-T001.

## Handoff

Architect: reconcile `SPRINT_049.md` / `S049_WAVE0_DECISIONS.md` /
`docs/planning/ROADMAP_PHASE_14_PROPOSAL.md` against this PRD's decisions
(framework-owned NumPy parameter format for v1 instead of pinned joblib;
last-fold promotion confirmed; BTC futures target confirmed; exact-match
parity, not tolerance-bounded, as the release gate) and produce an updated
Wave 0 decision set plus the ADR this mechanism requires — including the
narrow amendment to ADR-0023 §7 flagged above. **Done:** ADR-0029 is written
and ACCEPTED; every Wave 0 fork went back to the maintainer before `engineer`
started.
