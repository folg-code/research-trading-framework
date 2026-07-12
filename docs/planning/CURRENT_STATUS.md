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
Current Phase: Phase 4 — Market Analysis Components and Multitimeframe (planning)
Current Milestone: Sprint 004 — Multitimeframe Foundation MVP
Implementation Status: Sprint 003 COMPLETE on main; Sprint 004 IN_PROGRESS (Wave 2 complete)
Overall Status: IN_PROGRESS
Active Sprint: SPRINT_004 (IN_PROGRESS — Wave 2 complete, Wave 3 next)
Last Completed Sprint: SPRINT_003 (COMPLETED)
```

---

## 3. Current Objective

Plan and execute **Sprint 004 — Multitimeframe Foundation MVP** (first increment of Phase 4).

Extend the Market Analysis Engine for safe multitimeframe batch analysis with a **lean MVP**:
explicit `ResampleNode`, `computation_timeframe` on requests, layered cache identity,
Polars resample/align path, `LAST_CLOSED_BAR` + `join_asof`, fixed UTC boundaries.
Trading Calendar deferred. Validate through vertical slice `1m → 5m ATR (aligned to 1m) + 1m EMA`.

Sprint 004 plan: `docs/planning/sprints/SPRINT_004.md`  
MTF architecture (vision): `docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md`  
Engine baseline (complete): Sprint 003 on `main`  
Sprint 003 record: `docs/planning/sprints/SPRINT_003.md`

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

### Sprint 004 — Multitimeframe Foundation MVP

**Status:** IN_PROGRESS (Wave 2 complete)  
**Plan:** `docs/planning/sprints/SPRINT_004.md`  
**Sprint branch:** `sprint/market-analysis-mtf`  
**Tasks:** 16 (T001–T008 DONE; Wave 3 next; T016 deferred)

**Design stance:** lean MTF MVP — layered identity, `ResampleNode` (not registry component), Polars for resample/align only, Trading Calendar deferred, ~5 outcome-scoped PRs. See Design Principles in sprint plan.

**Prerequisite:** [`ARCHITECTURE_SIMPLIFICATION_REVIEW_S002_S003.md`](retrospectives/ARCHITECTURE_SIMPLIFICATION_REVIEW_S002_S003.md) — forward direction Polars-first; do not rewrite S002/S003; TD-011–TD-016 track accepted debt.

**Planned waves:**

- Wave 0 — single MTF spike + architecture decision note (T001)
- Wave 1 — timeframe on request/context, resolved model, layered identities, `ResampleSpec` (T002–T005)
- Wave 2 — Polars resampling, request resolution, planner/executor `ResampleNode` (T006–T008)
- Wave 3 — `available_at`, `join_asof` alignment, frame MTF assembly (T009–T011)
- Wave 4 — behavior tests + end-to-end vertical slice (T012–T013)
- Wave 5 — one ADR (ADR-MA-012), docs, closure (T014–T015)

**Next:** Wave 3 (T009–T011) — `available_at`, `join_asof` alignment, frame MTF assembly.

**Reference:** `docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md`, `docs/agents/AGENTS_MULTITIMEFRAME_MARKET_MODEL_UPDATED (1).md`

---

## 7. Blocked Work

Nothing is technically blocked.

Sprint 004 Wave 2 (T006–T008) complete — **Wave 3 next**.

---

## 8. Open Critical Problems

From `PROBLEM_REGISTRY.md` — Sprint 004 addresses:

- PRB-002 — layered computation identity (Resample / Component / Alignment),
- PRB-007 — **deferral note only** (fixed UTC resampling; exchange calendar in Sprint 005+).

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
Sprint 004 — Multitimeframe Foundation MVP (active plan)
```

Target flow after Sprint 004:

```text
Published DatasetRef (1m)
    → explicit Resample node (e.g. 5m)
    → timeframe-aware component DAG
    → LAST_CLOSED_BAR alignment to evaluation grid
    → AnalysisResultStore → AnalysisWorkspace → AnalysisFrame
```

Deferred to Sprint 005+ within Phase 4:

```text
Structure catalog (Pivot, swing labels)
MarketFieldReference and model expression evaluation
exchange/session calendar
persistent derived datasets
optional TA-Lib adapter (S003-T027 / S004-T034)
```

---

## 12. Sprint Progress

| Sprint | Goal | Status | Progress |
|--------|------|--------|----------|
| 001 | Repository foundation | COMPLETED | 22 / 22 tasks |
| 002 | Market Data MVP | COMPLETED | 26 / 26 tasks |
| 003 | Market Analysis Engine MVP | COMPLETED | 40 / 41 tasks (T027 deferred) |
| 004 | Multitimeframe Foundation MVP | IN_PROGRESS | 5 / 15 tasks (T016 deferred) |

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
