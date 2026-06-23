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
Current Phase: Phase 2 — Market Data MVP
Current Milestone: Sprint 002 — Market Data MVP
Implementation Status: Sprint 002 complete on integration branch
Overall Status: IN_PROGRESS
Active Sprint: SPRINT_002 (COMPLETED — pending merge to main)
Last Completed Sprint: SPRINT_001 (COMPLETED)
```

---

## 3. Current Objective

Execute **Sprint 002 — Market Data MVP**.

Deliver the first reproducible OHLCV import flow from external CSV through publication to historical query.

Sprint 002 plan: `docs/planning/sprints/SPRINT_002.md`  
Sprint 001 record: `docs/planning/sprints/SPRINT_001.md`

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
- core exceptions: `TradingFrameworkError`, `ValidationError`, `ConfigurationError`,
- `Identifier` base value object,
- UTC timestamp normalization (`require_utc_aware`, `normalize_to_utc`),
- `Timeframe` value object,
- `Clock` protocol with `SystemClock` and `FixedClock`,
- `FrameworkConfig`, TOML loading, logging configuration,
- architecture boundary test (no `user_data/` imports from `src/`),
- test structure: `unit/`, `integration/`, `e2e/` (36 unit tests),
- root `AGENTS.md` and `README.md`,
- ADR-0001, ADR-0002, ADR-0003.

### Phase 2 — Market Data MVP (Sprint 002)

Completed on `sprint/market-data-mvp`:

- MVP numeric types (`Price`, `Volume`) and `MarketBar`,
- dataset identity (`DatasetId`, `DatasetRef`) and metadata,
- dataset lifecycle `WORKING → FINALIZED → PUBLISHED`,
- CSV inspection, normalization, validation and import infrastructure,
- Parquet writer, dataset registry and repository,
- application workflows: import, finalize, publish, query,
- ADR-0007, ADR-0008,
- unit, contract and integration test coverage for the CSV vertical slice.

### Architectural Foundations

Conceptual architecture for all major domains remains as previously defined in `docs/architecture/`.

---

## 5. Documentation Baseline

```text
AGENTS.md
README.md
user_data/README.md
docs/architecture/
docs/agents/
docs/planning/
docs/adr/ADR-0001-modular-monolith.md
docs/adr/ADR-0002-separate-src-and-user-data.md
docs/adr/ADR-0003-utc-internal-time.md
docs/adr/ADR-0007-dataset-lifecycle-and-publication.md
docs/adr/ADR-0008-parquet-historical-storage.md
docs/planning/sprints/SPRINT_001.md
docs/planning/sprints/SPRINT_002.md
```

---

## 6. Work in Progress

### Sprint 002 — Market Data MVP

**Status:** COMPLETED on `sprint/market-data-mvp` (integration merge to `main` pending)  
**Plan:** `docs/planning/sprints/SPRINT_002.md`  
**Tasks:** 26 / 26 complete on sprint branch

Wave 6 verification PRs may still be open at review time:

- `sprint/market-data-mvp--market-data-fixtures`
- `sprint/market-data-mvp--csv-import-integration-test`
- `sprint/market-data-mvp--dataset-and-storage-adrs`

Next: sprint integration review and PR from `sprint/market-data-mvp` to `main`.

---

## 7. Blocked Work

Nothing is technically blocked.

Sprint 002 implementation is complete on the integration branch; remaining work is review and merge to `main`.

---

## 8. Open Critical Problems

Unchanged high-priority items from `PROBLEM_REGISTRY.md`:

1. Canonical numeric types for price, volume and quantity (PRB-010) — **MVP mitigated** for OHLCV CSV slice.
2. Dataset identity algorithm (PRB-001) — **MVP mitigated** for Sprint 002.
3. Component and model fingerprints (PRB-002, PRB-003).
4. Public `user_data/` discovery contract (PRB-004).
5. Market Analysis result storage schemas (PRB-005).
6. Research Dataset physical schemas (PRB-006).
7. Trading Calendar choice (PRB-007).
8. Vectorized backtest semantics (PRB-014).
9. Research/runtime parity (PRB-013).

PRB-015 (import boundaries) and PRB-016 (ADR materialization) are partially mitigated by Sprint 001.

---

## 9. Open Architectural Decisions

| ADR | Status |
|-----|--------|
| ADR-0001 Modular Monolith | ACCEPTED |
| ADR-0002 Separate src and user_data | ACCEPTED |
| ADR-0003 UTC Internal Time | ACCEPTED |
| ADR-0007 Dataset Lifecycle and Publication | ACCEPTED |
| ADR-0008 Parquet Historical Storage | ACCEPTED |
| ADR-0004 – ADR-0006, ADR-0009 – ADR-0010 | PLANNED |

---

## 10. Known Risks

- **Phase 2 scope creep** — first data slice must stay limited to one OHLCV flow.
- **Numeric type delay** — PRB-010 should be resolved early in Phase 2.
- **Documentation drift** — sprint and status documents must be updated with Phase 2 planning.

---

## 11. Next Planned Capability

```text
Sprint integration: merge sprint/market-data-mvp → main
```

Then choose the next Phase 2 increment:

```text
missing-range calculator, historical synchronization policy, or Parquet import
```

---

## 12. Sprint Progress

| Sprint | Goal | Status | Progress |
|--------|------|--------|----------|
| 001 | Repository foundation | COMPLETED | 22 / 22 tasks |
| 002 | Market Data MVP | COMPLETED (branch) | 26 / 26 tasks |

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
