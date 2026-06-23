# Architectural Decision Records

## Purpose

ADRs preserve **why** significant architectural decisions were made.

Architecture documents describe the current system. ADRs preserve decision history.

## Status Model

```text
PROPOSED
ACCEPTED
DEPRECATED
SUPERSEDED
```

## Index

| ADR | Title | Status | Sprint |
|-----|-------|--------|--------|
| [ADR-0001](ADR-0001-modular-monolith.md) | Modular Monolith | ACCEPTED | Sprint 001 |
| [ADR-0002](ADR-0002-separate-src-and-user-data.md) | Separate `src` and `user_data` | ACCEPTED | Sprint 001 |
| [ADR-0003](ADR-0003-utc-internal-time.md) | UTC Internal Time | ACCEPTED | Sprint 001 |
| [ADR-0007](ADR-0007-dataset-lifecycle-and-publication.md) | Dataset Lifecycle and Publication | ACCEPTED | Sprint 002 |
| [ADR-0008](ADR-0008-parquet-historical-storage.md) | Parquet Historical Storage | ACCEPTED | Sprint 002 |
| ADR-0004 | Independent Research and Execution Workflows | PLANNED | TBD |
| ADR-0005 | Market Analysis Domain and Taxonomy | PLANNED | TBD |
| ADR-0006 | Declarative Market and Signal Models | PLANNED | TBD |
| ADR-0009 | Batch Backtest vs Replay Execution | PLANNED | TBD |
| ADR-0010 | Working Component and Model Fingerprints | PLANNED | TBD |

Decisions ADR-0004 through ADR-0006 and ADR-0009 through ADR-0010 are already described in architecture documents. Individual ADR files will be created incrementally.

## Template

```markdown
# ADR-XXXX — Title

## Status

ACCEPTED | PROPOSED | DEPRECATED | SUPERSEDED

## Context

What problem or constraint led to this decision.

## Decision

What was decided.

## Consequences

Positive and negative outcomes of the decision.

## References

- links to architecture documents, problems, or superseding ADRs
```

## Related Documents

- `docs/architecture/ARCHITECTURE_FOUNDATIONS_UPDATED.md`
- `docs/architecture/ARCHITECTURE_TECHNICAL_UPDATED.md`
- `docs/architecture/WORKFLOWS_AI_ADR_UPDATED.md`
- `docs/planning/PROBLEM_REGISTRY.md` — PRB-016
