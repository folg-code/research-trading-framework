# Sprint 032 — Live Strategy Evaluation Parity

## Metadata

```text
Sprint: 032
Phase: Phase 8A polish
Status: IN_PROGRESS
Planned Start: 2026-07-18
Sprint Branch: sprint/live-strategy-eval-parity
Wave 0: docs/planning/sprints/S032_WAVE0_DECISIONS.md
Depends On: S031 Live Paper; Strategy Research evaluate_models / SignalModelEvaluator
```

## Goal

```text
Live paper evaluates StrategyModelDefinition via research stack
  → required_closed_bars from component warmup (+ firing lookback)
  → Bootstrap closed bars (Binance REST); then append each closed candle
  → Rolling-window full recompute (no incremental component state yet)
```

## Checklist

- [x] Wave 0 — decisions
- [x] Wave A — required_closed_bars_for_strategy
- [x] Wave B — REST bootstrap + rolling buffer sizing
- [x] Wave C — StrategyModelLiveSignalEvaluator via SignalModelEvaluator
- [x] Wave D — wire local/AWS dry-run + inspection docs
