# ADR-0003 — UTC Internal Time

## Status

ACCEPTED

## Context

Trading systems combine data from multiple providers, exchanges and timezones.
Naive or mixed timezone handling causes subtle reproducibility bugs, look-ahead bias and replay inconsistency.

## Decision

Use **UTC as the canonical internal timezone**:

- all internal timestamps must be timezone-aware,
- naive `datetime` values are rejected at normalization boundaries,
- local or exchange time is allowed only at system boundaries (adapters, UI, reports, configuration),
- time-dependent domain logic uses a `Clock` abstraction instead of `datetime.now()`.

Initial implementations: `SystemClock`, `FixedClock`.

## Consequences

### Positive

- consistent temporal semantics across modules,
- deterministic tests via `FixedClock`,
- explicit foundation for multitimeframe and replay correctness.

### Negative

- boundary adapters must perform explicit conversion,
- trading calendar and session logic remain future work (see PRB-007).

## References

- `src/trading_framework/time/`
- `docs/architecture/ARCHITECTURE_TECHNICAL_UPDATED.md` §2.2–2.8
- `docs/planning/PROBLEM_REGISTRY.md` — PRB-008, PRB-009
