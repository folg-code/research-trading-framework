# ADR-0001 — Modular Monolith

## Status

ACCEPTED

## Context

The Trading Research Framework spans multiple domains: Market, Market Analysis, Strategy, Research and Execution.
Early distribution across services would increase operational complexity before domain boundaries are validated through implementation.

## Decision

Adopt a **modular monolith** architecture:

- one deployable codebase,
- explicit domain packages under `src/trading_framework/`,
- strict dependency direction between domains,
- no premature service extraction.

Distribution into separate services is deferred until demonstrated needs justify it.

## Consequences

### Positive

- simpler local development and testing,
- lower operational overhead during research-heavy early phases,
- architectural boundaries can be enforced through imports and tests.

### Negative

- scaling and deployment flexibility are limited until a future split,
- discipline is required to prevent the monolith from becoming a god-object.

## References

- `docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md`
- `docs/planning/ROADMAP.md`
