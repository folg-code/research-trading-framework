# Market Analysis — Future Direction

Current component identity, dependency planning, batch multitimeframe computation and alignment are in [Market Analysis Architecture](../reference/system/MARKET_ANALYSIS_ARCHITECTURE.md), [Time and Alignment](../reference/system/TIME_AND_ALIGNMENT.md) and the [module guide](../reference/modules/MARKET_ANALYSIS.md). This page retains only proposed extensions. The [pre-review snapshot](../archive/snapshots/MARKET_ANALYSIS_FUTURE_pre_review.md) preserves the earlier mixed classification detail.

## State families

Reusable States can classify conditions built from market facts, Features and Structures, independent of a specific strategy. Candidate families include trend, volatility regime, momentum, liquidity, structural condition and market phase. These names describe a possible taxonomy, not a promise of matching current classes or a separate State output type.

## Explicit intrabar semantics

Partial higher-timeframe input should be available only through an explicit intrabar contract. It would declare update frequency, availability time, output stability, cache identity and research/runtime parity assumptions. Ordinary resampling must not accidentally expose an incomplete bar as a closed-bar value.

## Derived resampling datasets

If resampled data is published as a reusable dataset, its lineage should identify source dataset and version, source/target timeframe, boundary rules, calendar version, resampling policy and checksum where appropriate. The exact user-workspace layout is not set by this proposal; use [User Workspace](../reference/system/USER_WORKSPACE.md) for the current layout.

## Richer component request

A future explicit request shape may name source, computation and evaluation timeframes plus resampling/alignment policies. Today's `ComponentRequest` and `ResolvedComponentRequest` are different, narrower contracts; see [ADR-MA-012](../adr/ADR-MA-012-batch-multitimeframe-computation-with-polars.md). Decorator syntax, if offered, must produce an explicit serializable request and must not hide dependencies, warm-up, availability or lineage.
