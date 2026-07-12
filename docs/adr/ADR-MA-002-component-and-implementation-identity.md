# ADR-MA-002 — Component and Implementation Identity

## Status

ACCEPTED

## Context

The same semantic component (for example ATR) may have multiple backend implementations. Cache keys,
lineage and registry resolution require stable, distinct identity types.

## Decision

Separate semantic and backend identity:

| Type | Role |
|------|------|
| `ComponentId` | Stable semantic name (`volatility.atr`) |
| `ComponentVersion` | Semver of the component contract |
| `ImplementationId` | Backend adapter name (`numpy.atr`) |
| `ImplementationVersion` | Semver of the adapter |
| `ComputationIdentity` | Resolved execution node including parameters, dataset, timeframe and dependency keys |

`ComponentRequest` expresses intent; `ComputationIdentity` is produced after parameter
canonicalization and dependency resolution.

Rejected alternative: encoding parameters only in column aliases or a single string cache key.

## Consequences

### Positive

- multiple implementations per component,
- deterministic deduplication and cache lookup,
- lineage records both semantic and backend identity.

### Negative

- more types to maintain than a single string identifier.

## References

- `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md` — D-005, D-006, D-016
- `src/trading_framework/market_analysis/identity/`
