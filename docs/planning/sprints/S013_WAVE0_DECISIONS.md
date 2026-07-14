# Sprint 013 — Wave 0 Architecture Decisions (OHLCV Strategy Research MVP)

## Metadata

```text
Task: S013-T001
Sprint: 013 — OHLCV Strategy Research MVP (Phase 6A)
Status: COMPLETE (planning)
Planned Start: 2026-07-14
Branch: sprint/ohlcv-strategy-research-mvp
Direction: docs/planning/sprints/SPRINT_013.md
Depends on: SPRINT_012 merged to main (ADR-0015); SPRINT_006, 008 on main
Scope: bar-based historical simulation of complete Strategy Models
```

---

## 0. Rationale

Phase 5 (Signal Research) studies **signal behaviour** without execution semantics. Phase 6A closes the
gap by simulating **complete Strategy Models** on published OHLCV facts:

```text
Market Model × Signal Model × Exit Model × Risk Model
    ↓
bar-sequential historical simulation (explicit fill assumptions)
    ↓
trade-level results + equity history
    ↓
persistent Strategy Research run envelope
```

Sprint 013 does **not** require trades, quotes, options, Signal Research runs, or Replay Execution.
It reuses `evaluate_models` and canonical Sprint 006 models.

Post-sprint track decision (2026-07-14): **Phase 6A** chosen over Phase 2C.2 (quotes) and Phase 4B
(orderflow). Data-track expansion may resume in parallel after the first strategy vertical slice.

---

## 1. Input dataset

**Decision D-S013-01:** Input is a **PUBLISHED** OHLCV `DatasetRef`:

```text
data_type  = ohlcv
timeframe  = any supported bar timeframe (vertical slice: 1m or 5m fixtures)
provider   = csv | derived | other published bar provider
```

The workflow reads bars through existing `query_historical` / `ParquetDatasetRepository` contracts.
It does **not** import vendor archives or derive bars inline.

---

## 2. Strategy composition

**Decision D-S013-02:** A **Strategy Model** composes four independent model definitions:

```text
Market Model  — gates when strategy may act
Signal Model  — emits directional entry intents
Exit Model    — closes open positions (contract-based)
Risk Model    — position sizing and exposure limits (contract-based)
```

Position sizing remains part of the Risk Model in Version 1 (`ARCHITECTURE_TECHNICAL_UPDATED.md` §6.3).

**Decision D-S013-03:** Sprint 013 introduces **Exit Model** and **Risk Model** as small, explicit
contracts in `strategy/`. Market and Signal Models reuse Sprint 006 definitions unchanged.

**Decision D-S013-04:** `run_strategy_research` calls `evaluate_models` inline. A prior Signal
Research run is **not** required and must not be a workflow prerequisite.

---

## 3. Simulation vs Replay boundary

**Decision D-S013-05:** Sprint 013 delivers **batch bar-sequential simulation** only.

```text
Strategy Research (Sprint 013)  — vectorized/bar-sequential backtest, explicit assumptions
Replay Execution (future)       — runtime clock, order/fill events, separate module
```

No `OrderSubmitted`, `OrderFilled`, or broker adapters in this sprint. TD-009 accepted shortcut applies.

**Decision D-S013-06:** Unsupported semantics fail explicitly:

- intrabar stop/limit ambiguity,
- partial fills,
- multiple concurrent positions per instrument (MVP: at most one open position),
- market orders with unknown bar OHLC ordering.

---

## 4. Fill and cost assumptions (TD-009)

**Decision D-S013-07:** Introduce frozen `SimulationAssumptions` included in **run identity**:

```text
fill_policy_entry     = NEXT_BAR_OPEN
fill_policy_exit      = NEXT_BAR_OPEN
slippage_bps          = non-negative decimal (0 allowed)
commission_per_side   = non-negative decimal (flat per fill)
initial_capital       = positive decimal
```

Entry: when a gated signal fires at bar `t` (`available_at`), fill at **open of bar `t+1`** if that
bar exists; otherwise skip entry (no lookahead).

Exit: when exit condition fires at bar `t`, fill at **open of bar `t+1`** under the same rule.

Slippage adjusts fill price against trade direction (worse price). Commission applies per fill (entry
and exit separately).

**Decision D-S013-08:** Document in ADR-0016 that results are **not** live-parity claims. Assumption
fingerprint hashes normalized assumption fields for reproducibility.

Alternative fill policies (`SAME_BAR_CLOSE`, `MID_PRICE`) are deferred enum values.

---

## 5. Entry gating and signal alignment

**Decision D-S013-09:** Market Model conditioning uses existing `evaluate_models` combined scope:

- entry intents arise only when **both** Market Model and Signal Model evaluate true on the shared
  evaluation grid,
- use `available_at` from model emissions for causal ordering (no future-bar access).

Signal Research `reference_price` remains descriptive only. Simulation uses fill policy above, not
`reference_price`.

---

## 6. Exit and Risk MVP contracts

**Decision D-S013-10:** First **Exit Model** implementation: `FixedBarsExitModel`

```text
exit_after_bars: int   — close N bars after entry fill bar (inclusive counting on bar index)
```

**Decision D-S013-11:** First **Risk Model** implementation: `FixedQuantityRiskModel`

```text
quantity: Decimal   — fixed position size (1 unit in canonical example)
max_positions: 1    — single open position per instrument
```

Follow-up increments (stop-loss exit, percent-of-equity sizing) are out of scope.

---

## 7. Canonical vertical slice

**Decision D-S013-12:** End-to-end example reuses Sprint 006 canonical models:

```text
Market Model  — high_volatility (volatility.state == HIGH)
Signal Model  — higher_low_long (structure.higher_low_event, ON_EVENT)
Exit Model    — fixed 10-bar hold
Risk Model    — quantity = 1
Dataset       — committed OHLCV fixture or synthetic bars from tests/fixtures
```

Spike (T001): `tests/spike/run_strategy_research_spike.py` validates simulator + envelope layout
before Wave 1 contracts land.

---

## 8. Fact tables and persistence (PRB-006 partial)

**Decision D-S013-13:** Strategy Research MVP envelope mirrors Signal Research patterns:

```text
run_root/
  manifest.json
  trades.parquet      — one row per round-trip (or leg) simulated trade
  equity.parquet      — one row per bar (or per trade event) equity snapshot
```

### SimulatedTrade (trade facts)

```text
trade_id
strategy_model_id
instrument
direction
entry_signal_at       — emission available_at
entry_fill_at         — bar timestamp used for entry fill
entry_fill_price
exit_signal_at
exit_fill_at
exit_fill_price
quantity
gross_pnl
commission_paid
net_pnl
bars_held
exit_reason
source_dataset_ref
```

### EquityPoint (equity facts)

```text
observed_at
equity
drawdown
open_position_count
```

**Decision D-S013-14:** Repository under `research/datasets/strategy_research.py` with write + read
round-trip. Manifest records model definition refs, assumptions fingerprint, dataset ref, run
timestamps, framework version.

**Decision D-S013-15:** Resolve **partial PRB-006** for Strategy Research MVP only (same approach as
D-S008-16 for Signal Research). Multi-data heterogeneous schemas remain Phase 6B.

---

## 9. Application boundary

```text
strategy/                         ExitModel, RiskModel, StrategyModelDefinition, SimulatedTrade
research/simulation/              SimulationAssumptions, bar-sequential engine
research/datasets/                StrategyResearchRunEnvelope, repository
application/strategy_research/    run_strategy_research, analyze_strategy_research_run (minimal)
```

Inspection layer (HTML) is **out of scope** — defer to a follow-up sprint or reuse patterns from
Sprint 010 later.

---

## 10. Basic analytics (MVP)

**Decision D-S013-16:** `analyze_strategy_research_run` returns a minimal read-only summary:

```text
trade_count
win_count / loss_count
win_rate
net_pnl
gross_pnl
total_commission
max_drawdown
final_equity
```

No walk-forward, Monte Carlo, or robustness filters in Sprint 013.

---

## 11. Testing strategy

| Tier | Scope |
|------|--------|
| Unit | assumptions validation, fill price math, fixed exit/risk, engine edge cases |
| Integration | full workflow on synthetic/commit fixtures; repository round-trip |
| Spike | opt-in local script; not CI-gated initially |

Target: maintain green `ruff`, `mypy`, `pytest` on every PR.

---

## 12. Out of scope

- Replay Execution, paper/live adapters,
- Signal Research analytics changes,
- multi-position portfolios, pyramiding, options,
- intrabar stop/limit, partial fills,
- walk-forward / robustness (Phase 7),
- strategy HTML reports,
- `user_data/` discovery contract (PRB-004),
- formal model versioning / released definition registry (fingerprints experimental only).

---

## 13. ADR and documentation deliverables

- **ADR-0016** — OHLCV Strategy Research MVP: simulation assumptions, envelope schema, boundaries.
- Update `MODULE_MAP.md`, `DATA_WORKFLOWS.md`, `CURRENT_STATUS.md` on sprint closure.
- Update `docs/adr/README.md` index.

---

## 14. Decision index

| ID | Summary |
|----|---------|
| D-S013-01 | PUBLISHED OHLCV input via `query_historical` |
| D-S013-02 | Strategy = Market × Signal × Exit × Risk |
| D-S013-03 | New Exit/Risk contracts in `strategy/` |
| D-S013-04 | No Signal Research run prerequisite |
| D-S013-05 | Batch simulation only; Replay separate |
| D-S013-06 | Explicit failure for unsupported semantics |
| D-S013-07 | NEXT_BAR_OPEN fill; slippage + commission in assumptions |
| D-S013-08 | Assumptions in run identity; no live-parity claim |
| D-S013-09 | Combined model gating on `available_at` |
| D-S013-10 | FixedBarsExitModel MVP |
| D-S013-11 | FixedQuantityRiskModel MVP |
| D-S013-12 | Canonical high_vol × higher_low vertical slice |
| D-S013-13 | trades.parquet + equity.parquet envelope |
| D-S013-14 | StrategyResearch repository + manifest |
| D-S013-15 | Partial PRB-006 resolution (strategy slice) |
| D-S013-16 | Minimal analyze_strategy_research_run summary |
