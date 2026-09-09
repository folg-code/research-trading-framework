# Trading Research Framework

# CURRENT_STATUS.md

## 1. Purpose

This document provides a concise snapshot of the current state of the Trading Research Framework.

It answers:

- where the project is now,
- what has been completed,
- what is actively being prepared,
- what is blocked,
- what decisions remain open,
- what capability should be built next.

This file is a status summary.

It is not the operational task board, the sprint history, the ADR index, or
the problem/debt registry — each of those has its own canonical owner, linked
below. Detailed task state belongs in `docs/planning/sprints/`.

---

## 2. Status Metadata

```text
Status Date: 2026-09-09
Current Phase: Phase 15 — Predictive Research Catalog Expansion and
  Real-Data Study. Increment 15A (Sprint 051) is COMPLETE and merged to
  `main` (#409). Increment 15B (Sprint 052, the real-data BTC predictive
  study) is COMPLETE (8/8 tasks) and **merged to `main`** (#461, #462, #463,
  2026-09-08) — Phase 15 as a whole is COMPLETE. Verdict: split result — the
  BINARY/classification pass (`sklearn.logistic`) clears `S044_GATE.md`
  §1.4's strict per-fold bar and closes ROADMAP §13F's Q5 dependency; the
  REGRESSION pass does not. Full write-up:
  `docs/reference/BTC_PREDICTIVE_STUDY.md`.
  Phase 14 — Predictive Model Promotion. Increment 14A (Sprint 049) is
  COMPLETE and merged to `main` (#396). Increment 14B (Sprint 050) is not
  planned or started — Phase 14 as a whole is NOT complete (no Market
  Analysis component, State, executor change, or dry-run session exists);
  Q5 closing does not by itself satisfy 14B's remaining prerequisites
  (ADR-0030, the named downstream robustness plan).
  Phase 16 — Quant Research Workbench (APPROVED 2026-09-04). Increment 16B
  (Sprint 056, SampleSpec Foundation) is COMPLETE and merged to `main`
  (#457). Increment 16A (Sprint 057, Analyst Verdict Artifact) is COMPLETE
  (7/7 tasks) and **merged to `main`** (#471, 2026-09-08) — the integration
  PR from `sprint/analyst-verdict-artifact` closed this increment. Increment
  16C (Signal Quality Scoring, Sprint 058) is **COMPLETE** (6/6 tasks,
  2026-09-09) on working PRs #472-#478 into `sprint/signal-quality-scoring`
  — ADR-0033 (score delivery boundary) is ACCEPTED and implemented; TD-021
  is REPAID, TD-022's promotion branch is confirmed repaid (residual open),
  TD-029 is re-deferred to 16G in writing and in code. Integration of
  `sprint/signal-quality-scoring` into `main` is a separate,
  maintainer-reviewed step, not yet performed
  (`ROADMAP.md` §13H;
  `docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md`;
  `docs/planning/sprints/SPRINT_058.md`;
  `docs/adr/ADR-0033-predictive-score-delivery-boundary.md`;
  `docs/reference/BTC_SIGNAL_QUALITY_STUDY.md`).
  All phases through Phase 13 (Sprint 048, #383) are COMPLETE on `main`.
Active Sprint: none opened. SPRINT_058 (Signal Quality Scoring, Phase 16
  increment 16C) is COMPLETE (6/6 tasks) pending its integration PR into
  `main`. See `docs/planning/sprints/SPRINT_058.md` Closeout. SPRINT_057
  (Analyst Verdict Artifact, Phase 16 increment 16A) is COMPLETE (7/7
  tasks) and merged to `main` via #471. See
  `docs/planning/sprints/SPRINT_057.md` §13 Review and
  `S057_WAVE0_DECISIONS.md`.
Last Completed Sprint (cross-cutting, merged to `main`): SPRINT_055
  (Documentation Architecture Rebuild, high-level to low-level) — merged to
  `main` via #447. SPRINT_054 (Vision Reclassification and Reference
  Layering, Phase 6b + 10a) — merged to `main` via #434.
Last Completed Sprint (research track, merged to `main`): SPRINT_052
  (Real-Data BTC Predictive Study, Phase 15B) — 8/8 tasks, merged to `main`
  via #461/#462/#463; closes Phase 15 and ROADMAP §13F's Q5. SPRINT_051
  (Momentum and Regime Component Catalog, Phase 15A) — 11/11 tasks, merged
  to `main` via #409.
Last Completed Sprint (Phase 16 track, merged to `main`): SPRINT_056
  (SampleSpec Foundation, Phase 16 increment 16B) — 7/7 tasks, merged to
  `main` via #457. One item of technical debt left open (`TECHNICAL_DEBT.md`
  TD-031).
Last Completed Sprint (Phase 16 track, merged to `main`):
  SPRINT_057 (Analyst Verdict Artifact, Phase 16 increment 16A) — 7/7
  tasks, working PRs #464-#469 merged into `sprint/analyst-verdict-artifact`,
  which was then merged to `main` via #471 (2026-09-08).
  All three retrospective verdicts (S057-T005) matched the pre-declared
  expectations exactly; no threshold was adjusted. One item of technical
  debt left open (`TECHNICAL_DEBT.md` TD-033); `PROBLEM_REGISTRY.md`
  PRB-022 also logged during this sprint.
Overall Status: STABLE
Full sprint-by-sprint history: §12 below (compact index) and each sprint's
  own `docs/planning/sprints/SPRINT_XXX.md`.
```

---

## 3. Work in Progress

**No sprint currently open.** SPRINT_058 (Signal Quality Scoring, Phase 16
increment 16C) — 6/6 tasks, working PRs #472 (planning docs, ADR-0033),
#473 (T001, SIGNAL_QUALITY pipeline proof), #474 (T002, estimator
comparison + threshold sensitivity), #475+#476 (T003, scorer-reference
contract + a manifest-parsing robustness fix found by review), #477 (T004,
the Strategy Research score gate + a warm-up-sizing fix found by review),
#478 (T005, the real-data BTC worked example). This is the phase's key
vertical slice: a fitted, promoted `sklearn.logistic` scorer over real
`BTCUSDT.P` `signal_occurrences` was named by a Strategy Research config
via a bare content-addressed fingerprint (TD-021 REPAID), evaluated
in-process under the same `available_at` discipline as every other
component (never a fitted blob, TD-022's promotion branch confirmed
repaid), and the comparison came back a complete, honest **negative
result**: ROC AUC 0.524 (barely above the 0.507 random-permutation
baseline), 2 of 6,200 trades filtered at a non-cherry-picked threshold —
see `docs/reference/BTC_SIGNAL_QUALITY_STUDY.md`. TD-029 is re-deferred to
16G in writing and in code. No PR has been merged yet; working PRs land
into `sprint/signal-quality-scoring`. See
`docs/planning/sprints/SPRINT_058.md` Closeout for the full closure
record.

SPRINT_057 (Analyst Verdict Artifact, Phase
16 increment 16A) — 7/7 tasks, working PRs #464 (ADR-0032), #465 (rule
set), #466 (fact extraction), #467 (sidecar I/O), #468 (retrospective
application), #469 (dashboard display), all merged into
`sprint/analyst-verdict-artifact`, which was then merged to `main` via
#471 (2026-09-08). `research/predictive/verdict.py` and
`application/predictive_research/evaluate_run_verdict.py` now produce a
reproducible, versioned verdict for a predictive run from persisted
artifacts alone; applied retrospectively to Sprint 052's three real runs,
all three matched the pre-declared expectations exactly (see
`docs/reference/PREDICTIVE_VERDICT.md` §4). One item of technical debt
left open (`TECHNICAL_DEBT.md` TD-033); `PROBLEM_REGISTRY.md` PRB-022 also
logged. No study, scorer, promotion, or new market claim was produced. See
`docs/planning/sprints/SPRINT_057.md` §13 Review for the full closure
record.

**Previously active (merged to `main`):** SPRINT_056 (SampleSpec
Foundation, Phase 16 increment 16B) — 7/7 tasks, merged via #457 (working
PRs #448, #449, #450, #451, #456). Contract types, sample provenance, real
`signal_occurrences` resolution, and a leakage-guard proof for
irregularly-spaced rows all shipped; no verdict, scorer, or study was
produced. One item of technical debt was left open (`TECHNICAL_DEBT.md`
TD-031). See `docs/planning/sprints/SPRINT_056.md` §13 Review for the full
closure record. SPRINT_055 (Documentation
Architecture Rebuild) — merged via #447. SPRINT_054 (Vision Reclassification
and Reference Layering, Phase 6b + 10a) — merged via #434, closing the two
items Sprint 053 deliberately deferred (vision-file reclassification and
`docs/reference/` layering) from
`docs/historical/REPO_WORKFLOW_DOCS_AUDIT.md`. See
`docs/planning/sprints/SPRINT_055.md` and `SPRINT_054.md` for task-level
status.

**Merged to `main` (2026-09-08):** SPRINT_052 (Real-Data BTC
Predictive Study, Phase 15B) — 8/8 tasks, tester/reviewer-approved, merged
via #461 (T003-T008 into `sprint/btc-predictive-study`), #462 (follow-up
fixes: off-by-one fold-date correction, `TECHNICAL_DEBT.md` TD-032), and
#463 (`sprint/btc-predictive-study` integration into `main`). Both baseline
passes (regression/ridge, binary/logistic) and the triggered tree pass ran
on real `BTCUSDT.P` data through the unmodified Phase 10 pipeline; the
write-up and Q5 disposition are recorded in
`docs/reference/BTC_PREDICTIVE_STUDY.md`. Q5 (ROADMAP §13F) is CLOSED by
the binary pass (run `faa6983acd03f846`, `sklearn.logistic`) — see
`docs/planning/sprints/SPRINT_052.md` §13 Review. This closes Phase 15 as a
whole.

**Next planned capability (APPROVED, three increments now complete):**
Phase 16 — Quant Research Workbench (increments 16A–16G), approved by the
maintainer 2026-09-04. Canonical description: `ROADMAP.md` §13H and
`docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H.1 (16A's
completion note) / §13H.2 (16B's completion note) / §13H.3 (16C's
completion note). **16B (Sprint 056) is complete and merged to `main`
(#457). 16A (Sprint 057) is complete (7/7 tasks) and merged to `main`
(#471). 16C (Sprint 058, Signal Quality Scoring) is COMPLETE** (6/6
tasks, 2026-09-09) — ADR-0033 (score delivery boundary) is ACCEPTED and
implemented; working PRs #472-#478 land into `sprint/signal-quality-
scoring`, not yet integrated to `main`. No other increment (16D–16G)
is opened, planned or numbered. Sprint 052 is not re-scoped or absorbed by
Phase 16.

---

## 4. Blocked Work

Nothing is currently blocked.

---

## 5. Open Problems, Decisions, and Risks

These have their own canonical owners — this file does not duplicate them:

- **Open problems:** [`PROBLEM_REGISTRY.md`](PROBLEM_REGISTRY.md)
- **Architectural decisions (ADR index):** [`../adr/README.md`](../adr/README.md)
- **Known technical debt:** [`TECHNICAL_DEBT.md`](TECHNICAL_DEBT.md)
- **Long-term roadmap / next planned capability:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation taxonomy:** [`../README.md`](../README.md)

---

## 6. Sprint Progress

| Sprint | Goal | Status | Progress |
|--------|------|--------|----------|
| 001 | Repository foundation | COMPLETED | 22 / 22 tasks |
| 002 | Market Data MVP | COMPLETED | 26 / 26 tasks |
| 003 | Market Analysis Engine MVP | COMPLETED | 40 / 41 tasks (T027 deferred) |
| 004 | Multitimeframe Foundation MVP | COMPLETED | 15 / 15 tasks (T016 deferred) |
| 005 | Calendar, swing structure, visual inspection | COMPLETED | 16 / 16 tasks (T017–T018 deferred) |
| 006 | Declarative Market Model and Signal Model | COMPLETED | 26 / 26 tasks |
| 007 | Research-enabling catalog | SKIPPED (scope gate) | 1 / 9 (T001 only) |
| 008 | Signal Research computation MVP | COMPLETED | 11 / 11 tasks |
| 009 | Combined research scopes | COMPLETED | 11 / 11 tasks |
| 010 | Signal Research analytics | COMPLETED | 11 / 11 tasks |
| 011 | Historical archive import — trades DBN (Phase 2B + 2C.1) | COMPLETED | 27 / 27 tasks |
| 012 | Derived OHLCV from trades (Phase 2B.3) | COMPLETED | 12 / 12 tasks |
| 013 | OHLCV Strategy Research MVP (Phase 6A) | COMPLETED | 15 / 15 tasks |
| 014 | Strategy Research dashboard Phase A | COMPLETED | 13 / 13 Phase A tasks |
| 015 | Continuous futures materialization (Phase 2C.4) | COMPLETED | 19 / 19 tasks |
| 016 | Robustness Research MVP (Phase 7) | COMPLETED | 34 / 34 tasks |
| 017 | Model Research Methodology MVP (Phase 5B) | COMPLETED | 10 / 10 tasks |
| 018 | Dry-run Execution contracts (Phase 8A) | COMPLETED | 2 / 2 Wave 0 tasks + execution contracts |
| 019 | Binance BTC Futures Live Data Adapter (Phase 8A) | COMPLETED | 9 / 9 tasks |
| 020 | Local BTC Futures Dry-Run Runtime (Phase 8A) | COMPLETED | 8 / 8 tasks |
| 021 | Execution Persistence and Read Model (Phase 8A) | COMPLETED | 8 / 8 tasks |
| 022 | AWS Runtime MVP for BTC Futures Dry Run (Phase 8A) | COMPLETED | integrated to main (#199) |
| 023 | OVH portfolio live dry-run dashboard (Phase 8A) | COMPLETED | integrated to main (#199 / #202); Streamlit is now primary UI |
| 024 | Dry-run reliability wiring (Phase 8A) | COMPLETED | main #270 (waves 1–4) |
| 025 | Streamlit dashboard polish + VPS publish | COMPLETED | main #249; deploy fixes #250/#251; edge TLS ops; user_data deferred |
| 026 | Research hot-path performance (Signal + Robustness) | COMPLETED | integrated to main (#215) |
| 027 | Market Data import / continuous build performance | COMPLETED | integrated to main (#220) |
| 028 | Dashboard Application MVP (Streamlit + DuckDB) | COMPLETED | integrated to main (#232) |
| 029 | Repository Layout Foundations | COMPLETED | integrated to main (#235) |
| 030 | Repository Navigability Hygiene | COMPLETED | integrated to main (#238) |
| 031 | Live Paper in Dashboard | COMPLETED | integrated to main (#241) |
| 032 | Live Strategy Evaluation Parity | COMPLETED | integrated to main (#246) |
| 033 | Dashboard presentation polish | COMPLETED | 6 / 6 tasks; Waves A–C (#253–#256); main #257 |
| 034 | Public Dashboard Demo Polish | COMPLETED | Waves 1–5 (#258–#259); main #260; VPS deploy; follow-ups #261–#264 |
| 035 | Next increment selection (post public demo) | COMPLETED | chose S024 then S036→S037→AI/ML |
| 036 | Research infra audit (DSL/component gate) | COMPLETED | 11 / 11 tasks; main #288 |
| 037 | Component libraries + DSL simplification | COMPLETED | 7 / 7 tasks; main #296 |
| 038 | Session Range Structure | COMPLETED | 6 / 6 tasks; main #300 |
| 039 | Predictive Research dataset foundation (Phase 10A) | COMPLETED | 20 / 20 tasks; main #309; working PRs #302–#308 |
| 040 | Baseline regression + classification (Phase 10A) | COMPLETED | 23 / 23 tasks; main #319; working PRs #310–#318 |
| 041 | Predictive Research report v1 (Phase 10A) | COMPLETED | 16 / 16 tasks; main #325; working PRs #320–#324 |
| 042 | Tree-based predictive models (Phase 10B) | COMPLETED | 22 / 22 tasks; main #335; working PRs #326–#334 |
| 043 | Neural predictive models (Phase 10C) | COMPLETED | 21 / 21 tasks; main #342; working PRs #336–#341 |
| 044 | Predictive dashboard + IDEA-014 gate (Phase 10C) | COMPLETED | 18 / 18 tasks; main #348; working PRs #343–#347 |
| 045 | Binance USD-M historical OHLCV ingestion (Phase 2F) | COMPLETED | 14 / 14 tasks; main #355; working PRs #350–#354 |
| 046 | Universal Operator CLI (Phase 11, `trading-cli`) | COMPLETED | 14 / 14 tasks; main #361; working PRs #356–#360 |
| 047 | Custom Strategy Authoring (Phase 12, `strategy_file` loader) | COMPLETED | 10 / 10 tasks; main #366; working PRs #363–#365 |
| 048 | Exit/Risk Model Expansion, Catalog Growth and New Strategies (Phase 13) | COMPLETED | 13 / 13 tasks; all four waves (#368-#381); merged to main via #383 |
| 049 | Promotable Predictive Artifact (Phase 14A) | COMPLETED | 15 / 15 tasks; all five waves (#385-#393); merged to main via #396; Phase 14A only — Phase 14 overall NOT complete (Sprint 050 / Phase 14B not started) |
| 051 | Momentum and Regime Component Catalog (Phase 15A) | COMPLETED | 11 / 11 tasks; all four waves (#397-#407); merged to main via #409; Phase 15A only — Phase 15 overall now COMPLETE (Sprint 052 / Phase 15B done, see next row) |
| 052 | Real-Data BTC Predictive Study (Phase 15B) | COMPLETED | 8 / 8 tasks; #460 (Wave 0 V=1m correction), #461 (T003-T008), #462 (follow-up fixes), #463 (integration to `main`); Q5 CLOSED by run `faa6983acd03f846` (`sklearn.logistic`) — see `docs/reference/BTC_PREDICTIVE_STUDY.md` and `docs/planning/sprints/SPRINT_052.md` §13 Review |
| 053 | Repository Workflow & Documentation Hygiene | IN PROGRESS | see `docs/planning/sprints/SPRINT_053.md` |
| 056 | SampleSpec Foundation (Phase 16, increment 16B) | COMPLETED | 7 / 7 tasks; working PRs #448, #449, #450, #451, #456; integrated to `main` via #457 — see `docs/planning/sprints/SPRINT_056.md` §13 Review |
| 057 | Analyst Verdict Artifact (Phase 16, increment 16A) | COMPLETED | 7 / 7 tasks; working PRs #464-#469 into `sprint/analyst-verdict-artifact`; integrated to `main` via #471 — see `docs/planning/sprints/SPRINT_057.md` §13 Review |
| 058 | Signal Quality Scoring (Phase 16, increment 16C) | COMPLETE | 6 / 6 tasks; working PRs #472-#478 into `sprint/signal-quality-scoring`; not yet integrated to `main`; real-data worked example came back a complete negative result — see `docs/planning/sprints/SPRINT_058.md` Closeout and `docs/reference/BTC_SIGNAL_QUALITY_STUDY.md` |

Sprint numbering has no gap at 050 — it is reserved for Phase 14B and not yet
opened (see `docs/planning/sprints/SPRINT_053.md` metadata for the numbering
rationale carried forward from Sprint 051).

---

## 7. Status Update Rules

Update this document when:

- a sprint begins or ends,
- the current phase changes,
- a critical blocker appears,
- an architectural decision materially changes direction (update the link
  target in §5, don't copy the decision here).

Do not use this file as a second task board, a second ADR index, a second
problem registry, or a sprint-by-sprint historical narrative — each of those
already has a canonical owner (§5, §6). Every sprint closure updates only
its own row in §6 and, if it's the active sprint, §2/§3 — it does not append
a new historical write-up to this file.
