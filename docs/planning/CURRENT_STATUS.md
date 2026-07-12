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

It is not the operational task board.

Detailed task state belongs in `docs/planning/sprints/` and, once configured, GitHub Issues and GitHub Projects.

---

## 2. Status Metadata

```text
Status Date: 2026-07-12
Current Phase: Phase 5 — Signal Research MVP (first increment)
Current Milestone: Sprint 008 — Signal Research computation
Implementation Status: Sprints 003–006 COMPLETE on main; Sprint 008 IN_PROGRESS
Overall Status: IN_PROGRESS
Active Sprint: SPRINT_008 (Wave 0)
Last Completed Sprint: SPRINT_006 (COMPLETED on main)
```

---

## 3. Current Objective

Execute **Sprint 008** per corrected direction: first Signal Research workflow end-to-end.

Binding direction: `docs/planning/sprints/PHASE_4_5_SPRINT_DIRECTION.md`  
Sprint 008 plan: `docs/planning/sprints/SPRINT_008.md`  
Wave 0: `docs/planning/sprints/S008_WAVE0_DECISIONS.md`

**North star:** published data → Signal Model → `SignalOccurrence` → forward outcomes → persistent research dataset (Sprints 008–010).

Shortest research path: `006 → 008` (Sprint 007 skipped at scope gate 2026-07-12).

---

## 4. Completed Capabilities

### Phase 0 — Project Governance

- planning documents, problem registry, roadmap and ADR index,
- Cursor rules and architecture documentation,
- Sprint 001 defined and completed.

Remaining non-blocking items: GitHub issue templates and Project board configuration.

### Phase 1 — Repository Foundation

Completed in Sprint 001:

- installable package (`trading_framework`, Python 3.12, uv, pydantic),
- quality toolchain: Ruff, mypy, pytest, pre-commit, GitHub Actions CI,
- domain package skeletons: `core`, `time`, `market`, `market_analysis`, `strategy`, `research`, `execution`, `events`, `config`, `infrastructure`, `application`,
- `user_data/README.md` placeholder and boundary documentation,
- core exceptions, `Identifier`, UTC time, `Timeframe`, `Clock`, `FrameworkConfig`,
- architecture boundary test,
- ADR-0001, ADR-0002, ADR-0003.

### Phase 2 — Market Data MVP

Completed in Sprint 002:

- `Instrument`, `MarketBar`, `DatasetRef`, `DatasetState`, lifecycle contracts,
- CSV inspect → normalize → validate → Parquet → register → finalize → publish → query,
- application workflows: `import_external_dataset`, `finalize_dataset`, `publish_dataset`, `query_historical`,
- integration test for full CSV import flow,
- ADR-0007 (dataset lifecycle), ADR-0008 (Parquet storage),
- CI triggers for `main` and `sprint/**` branches.

### Phase 3 — Market Analysis Engine MVP

Completed in Sprint 003 (merged to `main`):

- registry, DAG planner, sequential executor, execution cache, result store, workspace,
- NumPy adapter; vertical slice True Range → ATR → Volatility State + EMA,
- `AnalysisFrameAssembler`, `run_analysis` facade,
- ADR-0005, ADR-MA-001–011; 208 tests at sprint closure.

### Phase 4 — Multitimeframe Foundation (Sprint 004)

Completed on `main` (PR #60, 2026-07-12):

- timeframe roles: `computation_timeframe`, `evaluation_timeframe`, `RequestResolver`,
- `ResampleSpec`, `ResampleNode`, Polars resample/align, layered identities,
- `available_at` on HTF outputs, `LAST_CLOSED_BAR` + `join_asof` frame assembly,
- MTF behavior regressions and end-to-end vertical slice via `run_analysis`,
- ADR-MA-012; 240 tests at sprint closure.

### Phase 4 — Market Analysis Components (Sprint 005)

Completed on `main` (2026-07-12):

- batch `TradingSessionResolver` and `CmeEsRthSessionResolver` (CME ES RTH),
- session metadata enrichment on `run_analysis` path,
- `structure.swing` component with event/state outputs and HH/HL/LH/LL classification,
- per-output MTF alignment: `EVENT_AT_AVAILABLE` vs `LAST_CLOSED_BAR`,
- behavior tests, S005 MTF vertical slice, Plotly inspection spike,
- ADR-MA-013; 280 tests at sprint closure.

### Phase 4 — Declarative Models (Sprint 006)

Completed on `main` (PR #75, 2026-07-12):

- `model_expression/` IR, validation, dependency extraction, evaluation,
- `market_model/` and `signal_model/` evaluators with firing policies,
- `model_authoring/` DSL compiling to IR,
- `evaluate_models` application orchestration,
- canonical examples, inspection overlay, ADR-0006,
- 338 tests at sprint closure.

### Phase 5 — Signal Research (Sprint 008)

In progress on `sprint/signal-research-mvp`:

- Wave 0: outcome semantics spike and architecture decisions,
- target: `SignalOccurrence` → forward return / MFE / MAE → Parquet research dataset,
- scope: `SIGNAL_MODEL_ONLY`.

Pending: Sprint 007 skipped (scope gate — existing components sufficient).

### Architectural Foundations

Conceptual architecture: `docs/vision/`. As-implemented reference: `docs/reference/`.

Market Analysis (vision):

- `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md` (D-001–D-036),
- `docs/vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` (workspace, result store, frames; takes precedence on derived-data topics).

---

## 5. Documentation Baseline

Single index: **`docs/README.md`**

```text
docs/README.md                    taxonomy & reading paths
docs/vision/                      assumptions & target design
docs/reference/                   as-implemented (see reference/README.md)
docs/planning/                    status, roadmap, sprints
docs/adr/                         decision records
AGENTS.md
```

Maintenance: `.cursor/rules/documentation.mdc`

---

## 6. Work in Progress

### Sprint 008 — Signal Research Computation MVP

**Status:** IN_PROGRESS (Wave 3 complete)  
**Plan:** `docs/planning/sprints/SPRINT_008.md`  
**Wave 0:** `docs/planning/sprints/S008_WAVE0_DECISIONS.md`  
**Sprint branch:** `sprint/signal-research-mvp`  
**Tasks:** 8 / 11 done (T001–T008)

**Scope gate:** Sprint 007 skipped — existing components sufficient for first experiment.

---

### Sprint 006 — Closed

**Status:** COMPLETE on `main` (PR #75, 2026-07-12)  
**Plan:** `docs/planning/sprints/SPRINT_006.md`  
**ADR:** ADR-0006  
**Tasks:** 26 / 26 done

---

## 7. Blocked Work

Nothing is technically blocked for Sprint 008 Wave 0.

---

## 8. Open Critical Problems

From `PROBLEM_REGISTRY.md` — Sprint 004 delivered:

- PRB-002 — layered computation identity (Resample / Component / Alignment) — partial MVP resolution extended,
- PRB-007 — deferral documented (fixed UTC resampling; exchange calendar in Sprint 005+).

Sprint 005 delivered partial PRB-007 resolution (CME ES RTH batch resolver only).

Remaining high-priority items:

1. Public `user_data/` discovery contract (PRB-004).
2. Research Dataset physical schemas (PRB-006).
3. Full exchange/session Trading Calendar (PRB-007 — partial MVP only; Globex, missing-range, registry open).
4. Local model definition fingerprints (PRB-003).
5. Full component implementation fingerprints (PRB-002 — parameter identity resolved in MVP).
6. Vectorized backtest semantics (PRB-014).
7. Research/runtime parity (PRB-013).

PRB-001, PRB-008 and PRB-010 received MVP resolution in Sprint 002.  
PRB-002 and PRB-005 received partial MVP resolution in Sprint 003.

---

## 9. Open Architectural Decisions

| ADR | Status |
|-----|--------|
| ADR-0001 Modular Monolith | ACCEPTED |
| ADR-0002 Separate src and user_data | ACCEPTED |
| ADR-0003 UTC Internal Time | ACCEPTED |
| ADR-0007 Dataset Lifecycle | ACCEPTED (Sprint 002) |
| ADR-0008 Parquet Storage | ACCEPTED (Sprint 002) |
| ADR-0005 Market Analysis Domain | ACCEPTED (Sprint 003) |
| ADR-MA-001–011 Market Analysis Engine | ACCEPTED (Sprint 003) |
| ADR-MA-012 Batch MTF with Polars | ACCEPTED (Sprint 004) |
| ADR-MA-013 CME ES RTH + Swing Structure MTF | ACCEPTED (Sprint 005) |
| ADR-0006 | ACCEPTED (Sprint 006) |
| ADR-0004, ADR-0009, ADR-0010 | PLANNED |

Binding decisions D-001–D-036 and workspace invariants are documented in the architecture files above; ADR materialization is Sprint 003 Wave 6 (including ADR-MA-007 workspace).

---

## 10. Known Risks

- **Inherited S002/S003 complexity** — MarketBar list, AnalysisDataView, Store+Workspace+Cache; see Architecture Simplification Review and TD-011–TD-016. Sprint 004 must not stack new wrappers without checklist §5.
- **Phase 4 scope creep** — multitimeframe and component catalog can expand quickly; keep outcome-scoped PRs.
- **Polars boundary creep** — Polars for resample/align only until MarketFrame migration is explicitly planned.
- **Implementation fingerprint gap** — PRB-002 parameter identity is resolved; full implementation hashing remains for research parity.
- **TA-Lib optional path** — deferred T027/S004-T016; NumPy adapter is the CI reference backend.

---

## 11. Next Planned Capability

```text
Sprint 008 — Signal Research computation (active)
Sprint 009 — Combined research scopes (MARKET_MODEL_ONLY, MARKET_AND_SIGNAL)
Sprint 010 — Analytics on stored datasets
```

See `PHASE_4_5_SPRINT_DIRECTION.md` for Sprints 009–010.

---

## 12. Sprint Progress

| Sprint | Goal | Status | Progress |
|--------|------|--------|----------|
| 001 | Repository foundation | COMPLETED | 22 / 22 tasks |
| 002 | Market Data MVP | COMPLETED | 26 / 26 tasks |
| 003 | Market Analysis Engine MVP | COMPLETED | 40 / 41 tasks (T027 deferred) |
| 004 | Multitimeframe Foundation MVP | COMPLETED | 15 / 15 tasks (T016 deferred) |
| 005 | Calendar, swing structure, visual inspection | COMPLETED | 16 / 16 tasks (T017–T018 deferred) |
| 006 | Declarative Market Model and Signal Model | COMPLETED | 26 / 26 tasks |
| 007 | Research-enabling catalog | SKIPPED (scope gate) | 1 / 9 (T001 only) |
| 008 | Signal Research computation MVP | IN_PROGRESS | 1 / 11 tasks |

---

## 13. Status Update Rules

Update this document when:

- a sprint begins or ends,
- the current phase changes,
- a capability is completed,
- a critical blocker appears,
- an architectural decision materially changes direction,
- the next planned capability changes.

Do not use this file as a second task board.

Keep it concise enough to understand project state quickly.
