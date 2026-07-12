# ADR-MA-003 — Parameter Canonicalization and Fingerprinting

## Status

ACCEPTED

## Context

PRB-002 noted that component fingerprint boundaries were undefined. Sprint 003 needed deterministic
parameter identity for DAG nodes and cache keys without requiring full implementation hashing yet.

## Decision

Each component declares a typed `ParameterSchema`. Raw API input is validated and converted to
immutable `CanonicalParameters` with:

- defaults applied,
- unknown keys rejected,
- stable JSON-serializable ordering for fingerprinting.

`ComputationIdentity.parameters` uses canonical values only. Implementation hashing and transitive
dependency hashing remain **out of Sprint 003 MVP scope** (PRB-002 partially resolved).

## Consequences

### Positive

- deterministic node identity for `ATR(14)` vs `ATR(50)`,
- parameter validation at the API boundary.

### Negative

- full implementation fingerprint contract still open for research-grade reproducibility.

## References

- `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md` — D-007, D-009
- `docs/planning/PROBLEM_REGISTRY.md` — PRB-002 (MVP resolution note)
- `src/trading_framework/market_analysis/models/parameters.py`
