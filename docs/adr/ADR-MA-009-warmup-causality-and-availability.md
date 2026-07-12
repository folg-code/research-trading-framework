# ADR-MA-009 — Warm-up, Causality and Availability

## Status

ACCEPTED

## Context

Indicators require history before valid values exist. Backtest and live workflows need to know when a
value is causal, delayed or retrospective, and when it becomes available relative to market time.

## Decision

Each component declares:

- `HistoryRequirement` — bars needed before the requested range,
- `Causality` — `CAUSAL`, `DELAYED`, or `RETROSPECTIVE` (MVP components are causal),
- `AvailabilityMetadata` on each `AnalysisResult`.

Engine responsibilities:

1. extend `computation_range` using plan warm-up requirements,
2. validate output length and valid index range after execution,
3. expose warm-up metadata on results; adapters must not silently hide warm-up bars.

MVP uses same-bar availability policy for single-timeframe batch runs.

## Consequences

### Positive

- reproducible warm-up handling across adapters,
- future workflows can reject non-causal components.

### Negative

- multitimeframe availability semantics deferred.

## References

- `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md` — D-020–D-022
- `src/trading_framework/market_analysis/execution/warmup.py`
