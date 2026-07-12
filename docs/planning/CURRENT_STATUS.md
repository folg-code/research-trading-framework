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
Current Phase: Phase 4 — Market Analysis Components and Multitimeframe
Current Milestone: Sprint 004 merged to main (2026-07-12)
Implementation Status: Sprint 003 and Sprint 004 COMPLETE on main
Overall Status: IN_PROGRESS
Active Sprint: SPRINT_005 (PLANNED — see SPRINT_005.md)
Last Completed Sprint: SPRINT_004 (COMPLETED)
```

---

## 3. Current Objective

Execute **Sprint 005** per corrected direction: calendar + Pivot Structure + visual inspection.

Binding direction: `docs/planning/sprints/PHASE_4_5_SPRINT_DIRECTION.md`  
Sprint 005 plan: `docs/planning/sprints/SPRINT_005.md`

**North star:** published data → visually verified analysis → declarative Signal Model → `SignalOccurrence` → persistent research dataset (Sprints 006–008).

Shortest research path: `005 → 006 → 008` (Sprint 007 only as needed).

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

### Sprint 005 — Trading Calendar, Pivot Structure and Visual Inspection MVP

**Status:** PLANNED (Wave 0–1 complete)  
**Spike:** `docs/planning/sprints/S005_CALENDAR_SPIKE_AND_DECISIONS.md`  
**Plan:** `docs/planning/sprints/SPRINT_005.md`  
**Direction:** `docs/planning/sprints/PHASE_4_5_SPRINT_DIRECTION.md`  
**Sprint branch (planned):** `sprint/market-analysis-components`  
**Tasks:** 18 (16 planned + 2 deferred)

**Outcomes:** (A) CME ES RTH batch session resolver, (B) Pivot Structure with event + HH/HL/LH/LL state outputs, (C) local inspection chart in `user_data/development/`.

**Planned follow-on (not started):** Sprints 006–010 — see direction doc and `SPRINT_006.md` … `SPRINT_010.md`.

---

## 7. Blocked Work

Nothing is technically blocked.

Sprint 005 planned — create sprint branch when Wave 0 starts.

---

## 8. Open Critical Problems

From `PROBLEM_REGISTRY.md` — Sprint 004 delivered:

- PRB-002 — layered computation identity (Resample / Component / Alignment) — partial MVP resolution extended,
- PRB-007 — deferral documented (fixed UTC resampling; exchange calendar in Sprint 005+).

Remaining high-priority items:

1. Public `user_data/` discovery contract (PRB-004).
2. Research Dataset physical schemas (PRB-006).
3. Exchange/session-aware Trading Calendar (PRB-007 — deferred from Sprint 004).
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
| ADR-0004, ADR-0006, ADR-0009, ADR-0010 | PLANNED |

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
Sprint 005 — Calendar + Pivot + chart (active plan)
Sprint 006 — Declarative Market/Signal Model
Sprint 008 — Signal Research dataset (target milestone)
```

See `PHASE_4_5_SPRINT_DIRECTION.md` for Sprints 007, 009, 010.

---

## 12. Sprint Progress

| Sprint | Goal | Status | Progress |
|--------|------|--------|----------|
| 001 | Repository foundation | COMPLETED | 22 / 22 tasks |
| 002 | Market Data MVP | COMPLETED | 26 / 26 tasks |
| 003 | Market Analysis Engine MVP | COMPLETED | 40 / 41 tasks (T027 deferred) |
| 004 | Multitimeframe Foundation MVP | COMPLETED | 15 / 15 tasks (T016 deferred) |
| 005 | Calendar, Pivot, visual inspection | PLANNED | 0 / 16 tasks (T017–T018 deferred) |

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
