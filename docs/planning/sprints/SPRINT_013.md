# Sprint 013 — OHLCV Strategy Research MVP (Phase 6A)

## Metadata

```text
Sprint: 013
Phase: Phase 6A — OHLCV Strategy Research MVP
Status: IN_PROGRESS (Wave 0 planning)
Planned Start: 2026-07-14
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_012 (main), SPRINT_006, SPRINT_008 (main)
Sprint Branch: sprint/ohlcv-strategy-research-mvp
Task branch convention: feat/ | fix/ | docs/ (separate prefix, not nested under sprint ref)
Wave 0 decisions: docs/planning/sprints/S013_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/planning/ROADMAP.md (§10 Strategy Research)
  - docs/vision/ARCHITECTURE_TECHNICAL_UPDATED.md (§6.3, §7.2)
  - docs/vision/WORKFLOWS_AI_ADR_UPDATED.md
  - docs/planning/TECHNICAL_DEBT.md (TD-009)
  - docs/adr/ADR-0011, ADR-0012 (upstream research patterns)
Track choice: Phase 6A selected over 2C.2 (quotes) and 4B (orderflow) — 2026-07-14
```

---

## 0. Slice choice

Sprint 012 delivered **derived OHLCV** from published trades. Phase 5 delivered **Signal Research**
on published bars. Neither is a prerequisite for Phase 6A, but both strengthen the data path.

Sprint 013 delivers the first **Strategy Research** vertical slice:

```text
Published OHLCV → evaluate_models (Market × Signal)
    → bar-sequential simulation (Exit × Risk)
    → trades + equity facts → persistent envelope
```

**Out of scope:** Replay Execution, quotes, orderflow, options, walk-forward, robustness, HTML
reports, multi-data strategy research (Phase 6B).

---

## 1. Sprint Goal

```text
PUBLISHED OHLCV DatasetRef
    ↓
StrategyModelDefinition (Market × Signal × Exit × Risk)
    ↓
evaluate_models → gated entry emissions
    ↓
BarSequentialSimulator (SimulationAssumptions, TD-009)
    ↓
SimulatedTrade rows + EquityPoint history
    ↓
StrategyResearchRunEnvelope (manifest + Parquet)
    ↓
analyze_strategy_research_run → minimal summary metrics
```

Success: a **complete Strategy Model** can be simulated on OHLCV-backed facts with **documented,
reproducible assumptions** and persisted trade/equity outputs readable without re-running simulation.

---

## 2. Three Outcomes

| Outcome | Deliverable |
|---------|-------------|
| **A — Model contracts** | Exit Model, Risk Model, Strategy Model composition |
| **B — Simulation engine** | Bar-sequential simulator with explicit fill/cost assumptions |
| **C — Research workflow** | `run_strategy_research`, envelope persistence, E2E round-trip, minimal analytics |

---

## 3. Domain Boundary

```text
market_model/ / signal_model/     existing declarative models (Sprint 006)
strategy/                         ExitModel, RiskModel, StrategyModelDefinition, SimulatedTrade
research/simulation/              SimulationAssumptions, BarSequentialSimulator
research/datasets/                StrategyResearchRunEnvelope, repository
application/strategy_research/    run_strategy_research, analyze_strategy_research_run
application/model_evaluation/     evaluate_models (reuse, unchanged public contract)
```

### Price semantics (binding)

```text
reference_price   — Signal Research descriptive anchor (unchanged)
fill_price        — simulation entry/exit per SimulationAssumptions (NEXT_BAR_OPEN MVP)
entry_price       — use fill_price fields on SimulatedTrade; avoid ambiguous aliases
```

### Reuse — do not rebuild

```text
evaluate_models          — Market × Signal evaluation
canonical_examples       — first e2e strategy models
query_historical         — bar loading
SignalOccurrence types   — not required as intermediate artifact in MVP path
Parquet envelope pattern — follow Signal Research manifest conventions
```

---

## 4. Logical Dataset Schema

Two fact tables (see S013_WAVE0_DECISIONS §8):

- `trades.parquet` — simulated round-trips with fill timestamps and PnL decomposition
- `equity.parquet` — equity curve aligned to bar timestamps

Manifest includes: strategy model refs, simulation assumptions fingerprint, source dataset ref,
effective date range, framework version.

---

## 5. Task Board

### Wave 0 — Decisions and spike

| Task | Description | Status |
|------|-------------|--------|
| S013-T001 | Wave 0 decisions (`S013_WAVE0_DECISIONS.md`) + simulation spike script | DONE (planning) |

### Wave 1 — Contracts

| Task | Description | Status |
|------|-------------|--------|
| S013-T002 | `ExitModel` protocol + `FixedBarsExitModel` | DONE |
| S013-T003 | `RiskModel` protocol + `FixedQuantityRiskModel` | DONE |
| S013-T004 | `StrategyModelDefinition` composition + validation | DONE |
| S013-T005 | `SimulationAssumptions` + fill policy types + fingerprint | DONE |

### Wave 2 — Simulation engine

| Task | Description | Status |
|------|-------------|--------|
| S013-T006 | `BarSequentialSimulator` domain engine | DONE |
| S013-T007 | `SimulatedTrade` + `EquityPoint` fact types and Polars schemas | DONE |

### Wave 3 — Persistence and workflow

| Task | Description | Status |
|------|-------------|--------|
| S013-T008 | `StrategyResearchRunEnvelope`, manifest, repository (write + read) | DONE |
| S013-T009 | `run_strategy_research` application workflow | DONE |

### Wave 4 — Integration and tests

| Task | Description | Status |
|------|-------------|--------|
| S013-T010 | E2E integration: published OHLCV → run → read-back | DONE |
| S013-T011 | Unit tests: assumptions, fill math, engine edge cases | TODO |

### Wave 5 — Analytics, CLI, closure

| Task | Description | Status |
|------|-------------|--------|
| S013-T012 | `analyze_strategy_research_run` minimal summary | TODO |
| S013-T013 | CLI `scripts/strategy_research/run_strategy_research.py` (optional) | TODO |
| S013-T014 | ADR-0016 + `MODULE_MAP.md` + `DATA_WORKFLOWS.md` | TODO |
| S013-T015 | Sprint closure + `CURRENT_STATUS.md` update | TODO |

**Progress:** 10 / 15 tasks

---

## 6. Recommended PR sequence

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 1 | `docs/sprint-013-planning` | Wave 0 decisions + sprint doc + status |
| 2 | `feat/strategy-exit-risk-contracts` | T002–T005 contracts + unit tests |
| 3 | `feat/strategy-simulation-engine` | T006–T007 simulator |
| 4 | `feat/run-strategy-research` | T008–T009 workflow + repository |
| 5 | `feat/strategy-research-e2e` | T010–T011 integration + unit coverage |
| 6 | `feat/strategy-research-closure` | T012–T015 ADR, analytics, CLI, docs |

Each PR targets `sprint/ohlcv-strategy-research-mvp`. Final sprint integration PR → `main` when all
tasks complete.

---

## 7. Acceptance criteria

1. Canonical Strategy Model (high_vol × higher_low × fixed exit × fixed risk) runs end-to-end on a
   committed OHLCV fixture without manual steps.
2. Simulation assumptions are persisted and hashed in manifest; changing assumptions produces a
   distinct run identity.
3. `trades.parquet` and `equity.parquet` round-trip through repository read API.
4. `analyze_strategy_research_run` returns trade count, win rate, net PnL, max drawdown.
5. CI green: `ruff check`, `ruff format --check`, `mypy`, `pytest`.
6. ADR-0016 ACCEPTED; module map and data flows updated.

---

## 8. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Monolithic backtest engine | Split contracts / engine / persistence / workflow PRs |
| Unclear fill assumptions | Single binding policy in Wave 0; ADR documents TD-009 |
| Conflating simulation with Replay | Explicit boundary in decisions §3 |
| Bar-only assumptions baked in permanently | Engine interface accepts bar stream abstraction; 6B extends inputs later |
| PRB-014 vectorized semantics | MVP is intentionally sequential; document limitations |

---

## 9. Dependencies

**Required on main:**

- Phase 2A OHLCV lifecycle and `query_historical`
- Sprint 006 declarative models and `evaluate_models`
- Sprint 008+ Signal Research patterns (envelope layout reference only)

**Not required:**

- Signal Research run artifacts
- Trades or derived-bar datasets (OHLCV CSV fixtures sufficient for CI)
- Sprint 007 catalog

---

## 10. Quality gates

Every implementation PR must pass:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

---

## 11. Post-sprint direction

After Sprint 013 merges to `main`:

- **Phase 6B** — multi-data strategy research (when 2C/4B data exists),
- **Phase 7** — robustness on persisted strategy runs,
- **Phase 2C.2 / 4B** — resume data-track expansion in parallel if needed,
- **Replay Execution** — separate sprint family under `execution/`.

See `ROADMAP.md` §10–§11 and `CURRENT_STATUS.md`.
