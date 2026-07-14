# ADR-0016 — OHLCV Strategy Research MVP

## Status

ACCEPTED

## Context

Phase 5 (Sprints 008–010) delivered **Signal Research** — studying signal behaviour with forward outcomes,
without execution semantics.

Phase 6A (Sprint 013) must validate **Strategy Model** composition and historical simulation on published
OHLCV facts:

```text
Market Model × Signal Model × Exit Model × Risk Model
```

Wave 0 decisions (`S013_WAVE0_DECISIONS.md`) and TD-009 require a deliberately limited fill model and a
clear boundary from Replay Execution.

## Decision

### Strategy composition

A **Strategy Model** composes four independent definitions:

```text
Market Model  — gates when the strategy may act
Signal Model  — emits directional entry intents
Exit Model    — closes open positions (MVP: FixedBarsExitModel)
Risk Model    — position sizing (MVP: FixedQuantityRiskModel)
```

`run_strategy_research` calls `evaluate_models` inline. A prior Signal Research run is **not** required.

### Simulation semantics (TD-009)

Introduce frozen `SimulationAssumptions` included in run identity:

```text
fill_policy_entry     = NEXT_BAR_OPEN
fill_policy_exit      = NEXT_BAR_OPEN
slippage_bps          — non-negative
commission_per_side   — non-negative flat per fill
initial_capital       — positive
```

Entry and exit fills occur at the **open of the bar after** the signal bar. Results are **not** live-parity
claims.

Batch **bar-sequential** simulation only. Replay Execution, order events and broker adapters remain in the
Execution track.

### Entry gating

Entry intents arise only when **both** Market Model and Signal Model evaluate true on the shared evaluation
grid. Gating joins signal emissions to dense market state at `available_at`.

### Domain boundary

```text
strategy/                         ExitModel, RiskModel, StrategyModelDefinition
research/simulation/              SimulationAssumptions, BarSequentialSimulator, fact schemas
research/datasets/strategy_research.py   envelope + repository
application/strategy_research/    run_strategy_research, analyze_strategy_research_run
```

Signal Research `reference_price` remains descriptive only. Simulation uses fill policy, not
`reference_price`.

### Persistence layout

Strategy Research runs persist under:

```text
<storage_root>/strategy_research/<run_id>/
  manifest.json
  trades.parquet
  equity.parquet
```

Schema version: `strategy_research.v1`. Run identity hashes strategy model refs, exit/risk parameters,
source dataset, date range, framework version and simulation assumptions fingerprint.

### Analytics boundary

`analyze_strategy_research_run` returns a minimal read-only summary:

```text
trade_count, win_count, loss_count, win_rate
gross_pnl, net_pnl, total_commission
max_drawdown, final_equity
```

No HTML reports, walk-forward or robustness in Sprint 013.

### CLI

`scripts/strategy_research/run_strategy_research.py` runs the canonical vertical slice on a published OHLCV
dataset for local operator workflows.

## Consequences

### Positive

- First complete Strategy Research vertical slice on OHLCV-backed facts.
- Explicit, reproducible simulation assumptions in run identity.
- Reuses `evaluate_models`, `query_historical` and Signal Research envelope patterns.
- Clear separation from Replay Execution.

### Negative

- MVP supports only `FixedBarsExitModel` and `FixedQuantityRiskModel`.
- `NEXT_BAR_OPEN` only — no intrabar stop/limit or partial fills.
- Single open position per instrument; overlapping entries while in position are skipped.
- Bar-sequential engine — not a vectorized portfolio backtest (PRB-014 partial).

### Follow-up

- Phase 6B — multi-data strategy research when trades/orderflow/options facts exist.
- Phase 7 — robustness on persisted strategy runs.
- ADR-0009 — formalize Replay Execution vs batch simulation when Execution track starts.

## References

- `docs/planning/sprints/S013_WAVE0_DECISIONS.md`
- `docs/planning/sprints/SPRINT_013.md`
- `docs/planning/TECHNICAL_DEBT.md` — TD-009
- `docs/planning/ROADMAP.md` — §10 Phase 6A
- ADR-0011, ADR-0012 (upstream research envelope patterns)
