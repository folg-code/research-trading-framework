# Phase 15 — Predictive Research Catalog Expansion and Real-Data Study

```text
Status: APPROVED (maintainer, 2026-09-02) — 15A COMPLETE, 15B PLANNED but not opened
```

Full detail for `ROADMAP.md` §13G — this is the LIVE, canonically-updated location for this
phase; `ROADMAP.md` carries only a short pointer stub under the same section number.

**This file is expected to keep changing** as the phase progresses (Wave 0 decisions, sprint
openings, status flips). Unlike `docs/planning/ROADMAP_COMPLETED_PHASES.md` — which is
frozen history — edits to this phase's detail happen **HERE**, not by re-inflating the
`ROADMAP.md` stub.

Internal heading numbering is preserved exactly as it was in `ROADMAP.md`, so a citation of
the form `roadmap/PHASE_15_PREDICTIVE_CATALOG.md §13G` resolves, matching the convention
already used in `ROADMAP_COMPLETED_PHASES.md`.

---

# 13G. Phase 15 — Predictive Research Catalog Expansion and Real-Data Study (APPROVED)

**Status:** **APPROVED** (maintainer, 2026-09-02). Sprint 051 (increment 15A)
is **COMPLETE** (11/11, on `sprint/momentum-and-regime-catalog`; final
integration PR to `main` pending) — see `SPRINT_051.md` §13 Review. Sprint 052
(increment 15B) is **PLANNED but NOT approved/opened** (`SPRINT_052.md`,
`Status: PLANNED`); it now has its delivered prerequisite fact from Sprint
051 (`BTCUSDT.P`, 1m, `2024-01-01 -> 2026-06-29`, 911 days, 1,311,840 rows,
zero gaps — `S051_BTC_DATA_INVENTORY.md`), but opening it remains a separate
maintainer approval step. **Phase 15 as a whole is NOT complete** — no
real-data predictive study has been run.
**Product source:** `docs/product/PRD-predictive-research-catalog-expansion.md`
— the maintainer's grill-me discovery record; authoritative on scope,
non-goals and success metrics.
**Sprints:** Sprint 051 (increment 15A — catalog) and Sprint 052 (increment
15B — the real-data study).
**ADRs:** **none proposed.** The components follow the existing
`model_authoring` DSL / registry / NumPy-implementation pattern exactly
(precedent: `candle.wick` Sprint 047, `trend.ema_distance` and
`volatility.range_expansion` Sprint 048 — none needed its own ADR), and the
study runs the Phase 10 pipeline unmodified. If Sprint 052 finds the pipeline
must change to run a real-data study, that is a STOP-and-report finding that
would earn an ADR then — not now.

## Purpose

Phase 10 validated its whole methodology — leakage guards, purged/embargoed
walk-forward, estimator families — against **synthetic known-signal fixtures
only** (ADR-0023 §8, D-S039-CI-dataset). No real candidate model exists. §13F
records that gap as "Q5", a named prerequisite gating Phase 14B and the
ML-promotion PRD's success metrics 2 and 3.

This phase closes that gap — or reports, with the same rigour, that it cannot
be closed with an OHLCV-only catalog at this instrument and horizon. Both
outcomes are deliverable results.

```text
15A — Momentum and Regime Component Catalog        Sprint 051 (COMPLETE)
      momentum.rsi / momentum.macd / momentum.stochastic;
      volatility.relative_volatility, statistics.return_autocorrelation,
      statistics.return_distribution.
      SHARED catalog: consumable by rule-based Signal Models AND declarable
      as predictive FeatureSpec entries — one catalog, two consumers, exactly
      like every existing component. No ML-only component concept is created.
      Also carried the LONG-LEAD BTC data-acquisition task — SUCCEEDED,
      measured (BTCUSDT.P, 1m, 2024-01-01 -> 2026-06-29, 911 days,
      1,311,840 rows, zero gaps; S051_BTC_DATA_INVENTORY.md).
      Shipped NO study result and NO change to the Phase 10 pipeline.

15B — Real-Data BTC Predictive Study               Sprint 052 (NOT planned)
      One study on the imported BTCUSDT.P bars, through the UNMODIFIED
      build_predictive_dataset -> run_predictive_research ->
      analyze_predictive_run pipeline, reported against RANDOM_PERMUTATION
      per fold and pooled. Positive or negative, the result is written down.
      Ships NO new component and NO promotion work.
```

**Why two sprints, not one:** Sprint 051's acceptance is deterministic and
unit-testable; Sprint 052's acceptance is a reported comparison whose outcome
is unknown at planning time. Sprint 052 also has a hard external prerequisite
(real BTC data, network, maintainer wall-clock) not satisfied today —
bundling would let a data-acquisition stall block already-finished component
work from merging. Sprint 051 delivers standalone value even if Sprint 052 is
never opened.

## Binding rules

```text
OHLCV only. No orderflow, no options-derived, no cross-asset features
One instrument — BTCUSDT.P — and one horizon, consistent with ADR-0023 §9.
    NON-BTC DATA IS A HARD STOP, NOT A FALLBACK (maintainer, 2026-09-02):
    if the BTC import proves impractical, the work stops and returns to the
    maintainer. Substituting NQ.c.0 or any other instrument is forbidden —
    it would not satisfy this section's Q5 wording and would present a
    prerequisite as closed when it is not
ADR-0023 §8 is NOT reopened: CI fixtures stay synthetic-only, standard CI
    stays network-free. The real-data study is a maintainer-triggered
    research run, never a CI fixture and never a CI dependency
The Phase 10 pipeline is CONSUMED, never modified
NO estimator-family restriction is invented. §13F's linear/logistic limit is
    specific to ADR-0029's parity mechanism and is NOT inherited here
Sprint 049's artifact format, promotion store and evaluator are untouched
A negative result is a legitimate, reportable outcome — never repaired by
    adding features until something sticks
Sprint 050 / Phase 14B is not planned, resized or pre-empted by this phase;
    the only interface is supplying (or failing to supply) its Q5 input
```

## Dependencies

- Phase 10 complete (Sprints 039–044) — **satisfied** (#348),
- Phase 2F's Binance USD-M importer (Sprint 045, ADR-0025) — **the code was
  satisfied first; the data is now satisfied too.** Verified 2026-09-02: no
  `BTCUSDT.P` dataset had ever been imported at that point. Sprint 051 ran
  the import over the maintainer-fixed range and it **succeeded**:
  `BTCUSDT.P`, 1m, `2024-01-01 -> 2026-06-29` (911 days, 1,311,840 rows,
  zero gaps — measured, `S051_BTC_DATA_INVENTORY.md`), well within the
  wall-clock cost accepted as a known, priced cost (ADR-0025
  "Consequences") — the actual run took ~8m36s with zero rate-limit
  backoff,
- Phase 12/13's catalog and authoring work — consumed as precedent, unmodified.

## Main risks

- **The data acquisition risk is RESOLVED** — Sprint 051's import succeeded
  (measured: 911 days, 1,311,840 rows, zero gaps,
  `S051_BTC_DATA_INVENTORY.md`); the hard-stop-on-impracticability path
  (D-S051-07a) was never triggered.
- **The riskiest assumption:** the new components may add noise dimensions
  to overfit rather than signal — mitigated by the existing purge/embargo/
  permutation discipline and by treating a negative result as reportable.
- **MTF features are not expressible in a `PredictiveStudySpec` today** —
  verified in code (`FeatureSpec`, `AnalysisFrameColumnSpec` carry no
  computation timeframe). Single-timeframe-first is a structural fact, not a
  stylistic preference.
- **A negative result leaves this section's Q5 open**, and Sprint 050 then
  inherits S049 Wave 0's recorded option (b): promote a synthetic artifact
  as plumbing, loudly labelled — a maintainer decision, never a silent
  fallback.

## Out of scope

- orderflow / options-derived / cross-asset features,
- **any instrument other than `BTCUSDT.P`** — a study elsewhere would be
  separate, separately-approved work and would not close this section's Q5,
- any change to the promotion mechanism (Sprint 049) or Phase 14B's plan,
- MTF variants of the new components and the `FeatureSpec` contract change
  they would require,
- report/dashboard expansion for predictive results — the maintainer's
  stated third priority,
- promoting whatever this phase's study produces — that is Sprint 049's
  merged mechanism and the maintainer's separate act.

**Relationship to Phase 16 (§13H, APPROVED 2026-09-04).** Phase 15B /
Sprint 052 is the real-data study named as "Increment 1" in
`RESEARCH_SIMULATION_DEVELOPMENT_DIRECTION.md`. It is **not** re-scoped,
renumbered, or absorbed by Phase 16, and Phase 16's approval changed
nothing about it — Sprint 052 remains independently gated on its own
maintainer approval. Phase 16's 16A adds only the standardized, persisted
*verdict artifact* that Sprint 052's binding rule ("the Phase 10 pipeline
is CONSUMED, never modified") forbids Sprint 052 from building. Sprint 052
ships the verdict as prose; 16A makes it a contract. See §13H.0.
