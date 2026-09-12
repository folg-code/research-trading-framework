# Sprint 032 — Wave 0 Decisions

Date: 2026-07-18.

## D-S032-01 — Research stack for live entry signals

**Decision:** Live entry evaluation uses `run_analysis` / `evaluate_models` /
`SignalModelEvaluator` over a `StrategyModelDefinition`. The close>EMA-only
matcher is removed.

## D-S032-02 — Warmup from component history requirements

**Decision:** `required_closed_bars_for_strategy` aggregates
`max_history_requirement` from the analysis plan and adds firing-policy
lookback (+1 for `ON_TRUE_EDGE`). Under-warm buffers do not emit entries.

## D-S032-03 — Bootstrap then append

**Decision:** At worker/runtime start, bootstrap enough closed 1m bars via
Binance USD-M REST. Afterwards append each closed WebSocket candle into a
rolling buffer sized to `max(required_bars, configured_cap)`.

## D-S032-04 — Rolling-window recompute (not incremental kernels)

**Decision:** Each step recomputes the AnalysisFrame over the current buffer.
True per-component incremental state is deferred follow-up debt.

## D-S032-05 — FixedBars exit unchanged

**Decision:** Exit remains `_fixed_bar_exit_active` in the local BTC futures
runtime for this sprint.
