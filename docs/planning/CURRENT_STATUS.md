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
Status Date: 2026-06-23
Current Phase: Phase 3 — Market Analysis Engine MVP
Current Milestone: Sprint 003 — Market Analysis Engine MVP
Implementation Status: Wave 4 complete; Wave 5 (verification) next
Overall Status: IN_PROGRESS
Active Sprint: SPRINT_003 (IN_PROGRESS)
Last Completed Sprint: SPRINT_002 (COMPLETED)
```

---

## 3. Current Objective

Plan and execute **Sprint 003 — Market Analysis Engine MVP**.

Deliver a minimal deterministic analysis engine: registry, dependency DAG, sequential batch execution,
execution-scoped result store and workspace, in-memory execution cache, optional `AnalysisFrame`
assembly, and results with identity and lineage. Validate through vertical slice
`True Range → ATR → Volatility State` plus EMA and diagnostic outputs from a published `DatasetRef`.

Sprint 003 plan: `docs/planning/sprints/SPRINT_003.md`  
Architecture decisions (vision): `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md`  
Workspace design (vision): `docs/vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md`  
Sprint 002 record: `docs/planning/sprints/SPRINT_002.md`

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

### Sprint 003 — Market Analysis Engine MVP

**Status:** IN_PROGRESS (Waves 0–4 complete)  
**Plan:** `docs/planning/sprints/SPRINT_003.md`  
**Sprint branch:** `sprint/market-analysis-mvp`  
**Tasks:** 41 (32 done — Waves 0–4)

**Completed waves:**

- Wave 0 — architecture closure, spike, Definition of Ready
- Wave 1 — identity and core contracts (T005–T012)
- Wave 2 — registry, dependency planner, execution plan (T013–T018)
- Wave 3 — `AnalysisDataView`, result store, workspace, executor, cache, errors (T019–T024, T037–T038)
- Wave 4 — TR/ATR/state/EMA components, `AnalysisFrameAssembler`, `run_analysis` (T025–T026, T028–T029, T039–T040)

**Next:** Wave 5 — contract tests, integration test, ADRs (T030–T036, T041). Optional: T027 TA-Lib extra.

**Reference:** `docs/reference/MODULE_MAP.md`, `docs/reference/modules/MARKET_ANALYSIS_MODULE.md`

---

## 7. Blocked Work

Nothing is technically blocked.

Sprint 003 implementation is gated on Wave 0 Definition of Ready — **passed 2026-06-23**.

---

## 8. Open Critical Problems

From `PROBLEM_REGISTRY.md` — Sprint 003 addresses MVP slices of:

- PRB-002 — computation parameter fingerprinting (Wave 1),
- PRB-005 — analysis result storage shape (Wave 1).

Remaining high-priority items:

1. Public `user_data/` discovery contract (PRB-004).
2. Research Dataset physical schemas (PRB-006).
3. Trading Calendar choice (PRB-007).
4. Local model definition fingerprints (PRB-003).
5. Vectorized backtest semantics (PRB-014).
6. Research/runtime parity (PRB-013).

PRB-001, PRB-008 and PRB-010 received MVP resolution in Sprint 002.

---

## 9. Open Architectural Decisions

| ADR | Status |
|-----|--------|
| ADR-0001 Modular Monolith | ACCEPTED |
| ADR-0002 Separate src and user_data | ACCEPTED |
| ADR-0003 UTC Internal Time | ACCEPTED |
| ADR-0007 Dataset Lifecycle | ACCEPTED (Sprint 002) |
| ADR-0008 Parquet Storage | ACCEPTED (Sprint 002) |
| ADR-0005 Market Analysis Domain | PLANNED — Sprint 003 Wave 6 |
| ADR-0004, ADR-0006, ADR-0009, ADR-0010 | PLANNED |

Binding decisions D-001–D-036 and workspace invariants are documented in the architecture files above; ADR materialization is Sprint 003 Wave 6 (including ADR-MA-007 workspace).

---

## 10. Known Risks

- **Overengineering** — engine scope must stay minimal; vertical slice validates contracts.
- **Data view lock-in** — spike required before freezing `AnalysisDataView`.
- **Hidden copies** — read-only view and memory benchmark mitigate large-dataset risk.
- **Sprint size** — 36 tasks; strict out-of-scope list for MTF, persistent cache, parallel execution.

---

## 11. Next Planned Capability

```text
Phase 3 — Market Analysis Engine MVP
```

First flow:

```text
Published DatasetRef → AnalysisDataView → DAG → AnalysisResultStore → AnalysisWorkspace
→ optional AnalysisFrame (wide consumer view)
```

Vertical slice:

```text
True Range → ATR → Volatility State (+ EMA, diagnostic output)
```

---

## 12. Sprint Progress

| Sprint | Goal | Status | Progress |
|--------|------|--------|----------|
| 001 | Repository foundation | COMPLETED | 22 / 22 tasks |
| 002 | Market Data MVP | COMPLETED | 26 / 26 tasks |
| 003 | Market Analysis Engine MVP | IN_PROGRESS | 32 / 41 tasks |

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
