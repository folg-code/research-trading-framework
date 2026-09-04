# ADR-MA-009 — Warm-up, Causality and Availability

## Status

ACCEPTED

Amended 2026-08-25 for D-REP-05 (`available_at` as a first-class bulk input column).

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

## Amendment 2026-08-25 — first-class `available_at` (D-REP-05)

The `observed_at` / `available_at` distinction remains the look-ahead-bias control. Reconstructing
`available_at` from the evaluation timeframe is only equivalent when provider delay matches the
nominal bar interval.

Stage 3 therefore carries `available_at` as an **additive optional** column on the bulk analysis
input, asserts equality with the reconstructed value on fixtures, then makes the column required
once parity holds. If any fixture disagrees, stop and report — that is a look-ahead-bias finding,
not a defect in the column.

Reconstruction helpers (`derive_bar_interval`, duration-from-timeframe) stay as fallback only while
the column is optional.

## Consequences

### Positive

- reproducible warm-up handling across adapters,
- future workflows can reject non-causal components.

### Negative

- multitimeframe availability semantics deferred.

## References

- `docs/vision/MARKET_ANALYSIS_DECISIONS.md` (formerly `MARKET_ANALYSIS_WITH_DECISIONS.md`) — D-020–D-022
- `src/trading_framework/market_analysis/execution/warmup.py`
- `docs/planning/sprints/SPRINT_036_DATA_REPRESENTATION_AUDIT.md` (formerly `docs/reference/system/DATA_REPRESENTATION_AUDIT.md`) — D-REP-05
