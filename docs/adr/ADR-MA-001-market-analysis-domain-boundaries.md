# ADR-MA-001 — Market Analysis Domain Boundaries

## Status

ACCEPTED

## Context

Market Analysis sits between published market datasets and higher-level research or execution workflows.
Without explicit boundaries, indicator logic leaks into strategies or data ingestion.

## Decision

Market Analysis **owns**:

- component and implementation identity,
- parameter schemas and canonicalization,
- dependency planning and batch execution,
- execution-scoped result storage and workspace,
- optional consumer frame assembly.

Market Analysis **does not own**:

- dataset import, normalization or publication (Market Data domain),
- strategy or signal semantics,
- order routing or live execution,
- persistent derived-dataset storage in Sprint 003.

Components receive a read-only `AnalysisDataView`; the application layer loads data from published
`DatasetRef` values through adapters.

## Consequences

### Positive

- testable domain with no hidden I/O in components,
- clear adapter boundary for NumPy, TA-Lib or future backends.

### Negative

- every workflow must pass through engine/application facades rather than ad-hoc column mutation.

## References

- `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md` — D-001, D-011, D-013
- ADR-0005, ADR-MA-004
