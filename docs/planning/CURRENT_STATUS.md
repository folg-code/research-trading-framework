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
Status Date: 2026-09-10
Current Phase: Phase 16 — Quant Research Workbench. Increments 16A–16C are
  COMPLETE. Increment 16D — Portfolio Dashboard — is in progress.
Current Increment: 16D — Portfolio Dashboard, IN PROGRESS. The accepted
  `DASHBOARD_DEVELOPMENT_DIRECTION.md` is authoritative for this increment
  and replaces the former Quant Lab framing. The feature PRD is ACCEPTED.
  Sprints 059 and 060 are COMPLETE; Sprint 061 completes the public story,
  catalog migration and production publication lifecycle.
Active Sprint: SPRINT_061 — Portfolio Story, Content and Direction
  Completion. Decisions D061-01 through D061-04 were accepted by the
  maintainer on 2026-09-10. T001 is Done (#503). T002–T004 are Done (#506)
  after the maintainer accepted the rendered content and architecture.
  T005 is Done (#510, #511); T006 is Done (#512–#515); T007 is Done
  (#516, #517), and T008 awaits final maintainer acceptance after green QA.
Last Completed Sprint: SPRINT_060 — Signal Quality Portfolio Evidence
  (Phase 16D), 6/6 tasks, merged to `main` via #498 (2026-09-10). It shipped
  the first real Signal Quality publication and persisted-evidence path over
  ADR-0034's deny-by-default projection.
Parallel state: Phase 15 is COMPLETE. Phase 14A is COMPLETE; Phase 14B /
  reserved Sprint 050 remains not planned and not started.
Overall Status: STABLE
Full sprint-by-sprint history: §12 below (compact index) and each sprint's
  own `docs/planning/sprints/SPRINT_XXX.md`.
```

---

## 3. Work in Progress

**SPRINT_061 is active at its final acceptance gate.** T001's claim/evidence
matrix is merged (#503).
T002–T004 are merged to the sprint branch (#506) after maintainer acceptance:
the dashboard now explains the modular data/research architecture, six
independent workflows, backtester, temporal correctness, Predictive Research
and the two explicitly future-only directions. T005 extended the safe
projection to every supported, safely identifiable catalog run and recorded
the approved visibility/grouping/release decisions (#510, #511). T006 shipped
the projection-backed grouped catalog and technical-page migration (#512–#515).
T007 shipped immutable production release wiring and root quality coverage
(#516, #517). T008 automated, independent and desktop QA are green; only final
maintainer factual/editorial acceptance remains.

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

**Current capability:** Phase 16D — Portfolio Dashboard. Sprints 059 and 060
are complete; Sprint 061 is the active completion sprint. Increments 16E–16G
remain directional and are not pulled into this plan.

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
| 058 | Signal Quality Scoring (Phase 16, increment 16C) | COMPLETED | 6 / 6 tasks; working PRs #472-#479; integrated to `main` via #480; real-data worked example produced a complete negative result — see `docs/planning/sprints/SPRINT_058.md` Closeout and `docs/reference/BTC_SIGNAL_QUALITY_STUDY.md` |
| 059 | Portfolio Publication Foundation (Phase 16, increment 16D) | COMPLETED | 6 / 6 tasks; working PRs #484-#489; integrated to `main` via #490 — see `docs/planning/sprints/SPRINT_059.md` §Closeout |
| 060 | Signal Quality Portfolio Evidence (Phase 16, increment 16D) | COMPLETED | 6/6 tasks; working PRs #491-#496; integrated to `main` via #498 — see `docs/planning/sprints/SPRINT_060.md` |
| 061 | Portfolio Story, Content and Direction Completion (Phase 16, increment 16D) | IN PROGRESS | T001–T007 Done (#503, #506, #510–#517); T008 QA green, maintainer acceptance pending — see `docs/planning/sprints/SPRINT_061.md` |

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
