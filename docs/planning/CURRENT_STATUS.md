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
Status Date: 2026-06-19
Current Phase: Phase 2 — Market Data MVP
Current Milestone: Sprint 002 — Market Data MVP
Implementation Status: Sprint planned, not started
Overall Status: IN_PROGRESS
Active Sprint: SPRINT_002 (PLANNED)
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
docs/planning/sprints/SPRINT_001.md
docs/planning/sprints/SPRINT_002.md
```

---

## 6. Work in Progress

### Sprint 002 — Market Data MVP

**Status:** PLANNED  
**Plan:** `docs/planning/sprints/SPRINT_002.md`  
**Tasks:** 26 (0 started)

First implementation wave resolves PRB-001, PRB-008 and PRB-010, then delivers domain models, CSV import, Parquet storage, lifecycle workflows and integration tests.

No implementation task is marked IN_PROGRESS yet.

---

## 7. Blocked Work

Nothing is technically blocked.

Phase 2 should define Sprint 002 before implementation begins.

---

## 8. Open Critical Problems

Unchanged high-priority items from `PROBLEM_REGISTRY.md`:

1. Canonical numeric types for price, volume and quantity (PRB-010).
2. Dataset identity algorithm (PRB-001).
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
| ADR-0004 – ADR-0010 | PLANNED |

---

## 10. Known Risks

- **Phase 2 scope creep** — first data slice must stay limited to one OHLCV flow.
- **Numeric type delay** — PRB-010 should be resolved early in Phase 2.
- **Documentation drift** — sprint and status documents must be updated with Phase 2 planning.

---

## 11. Next Planned Capability

```text
Phase 2 — Market Data MVP
```

First flow:

```text
External OHLCV File → Inspect → Normalize → Validate → Store → Register → Query
```

---

## 12. Sprint Progress

| Sprint | Goal | Status | Progress |
|--------|------|--------|----------|
| 001 | Repository foundation | COMPLETED | 22 / 22 tasks |
| 002 | Market Data MVP | PLANNED | 0 / 26 tasks |

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
