# Architectural Decision Records

Catalog of `docs/adr/`. For documentation taxonomy see **[../README.md](../README.md)**.

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
| [ADR-0005](ADR-0005-market-analysis-domain-and-taxonomy.md) | Market Analysis Domain and Taxonomy | ACCEPTED | Sprint 003 |
| [ADR-0007](ADR-0007-dataset-lifecycle-and-publication.md) | Dataset Lifecycle and Publication | ACCEPTED | Sprint 002 |
| [ADR-0008](ADR-0008-parquet-historical-storage.md) | Parquet Historical Storage | ACCEPTED | Sprint 002 |
| [ADR-MA-001](ADR-MA-001-market-analysis-domain-boundaries.md) | Market Analysis Domain Boundaries | ACCEPTED | Sprint 003 |
| [ADR-MA-002](ADR-MA-002-component-and-implementation-identity.md) | Component and Implementation Identity | ACCEPTED | Sprint 003 |
| [ADR-MA-003](ADR-MA-003-parameter-canonicalization-and-fingerprinting.md) | Parameter Canonicalization and Fingerprinting | ACCEPTED | Sprint 003 |
| [ADR-MA-004](ADR-MA-004-analysis-data-view-and-data-ownership.md) | AnalysisDataView and Data Ownership | ACCEPTED | Sprint 003 |
| [ADR-MA-005](ADR-MA-005-analysis-result-and-output-identity.md) | AnalysisResult and Output Identity | ACCEPTED | Sprint 003 |
| [ADR-MA-006](ADR-MA-006-dependency-dag-and-execution-planning.md) | Dependency DAG and Execution Planning | ACCEPTED | Sprint 003 |
| [ADR-MA-007](ADR-MA-007-analysis-workspace-and-derived-data.md) | Analysis Workspace and Derived Data | ACCEPTED | Sprint 003 |
| [ADR-MA-008](ADR-MA-008-cache-identity-and-cache-scope.md) | Cache Identity and Cache Scope | ACCEPTED | Sprint 003 |
| [ADR-MA-009](ADR-MA-009-warmup-causality-and-availability.md) | Warm-up, Causality and Availability | ACCEPTED | Sprint 003 |
| [ADR-MA-010](ADR-MA-010-external-analytical-libraries.md) | External Analytical Libraries | ACCEPTED | Sprint 003 |
| [ADR-MA-011](ADR-MA-011-batch-versus-incremental-execution.md) | Batch Versus Incremental Execution | ACCEPTED | Sprint 003 |
| [ADR-MA-012](ADR-MA-012-batch-multitimeframe-computation-with-polars.md) | Batch Multitimeframe Computation with Polars | ACCEPTED | Sprint 004 |
| [ADR-MA-013](ADR-MA-013-cme-es-rth-session-and-swing-structure-mtf-projection.md) | CME ES RTH Session and Swing Structure MTF Projection | ACCEPTED | Sprint 005 |
| [ADR-0006](ADR-0006-declarative-market-and-signal-models.md) | Declarative Market and Signal Models | ACCEPTED | Sprint 006 |
| [ADR-0011](ADR-0011-signal-research-outcomes-and-persistence.md) | Signal Research Outcomes and Persistence | ACCEPTED | Sprint 008 |
| [ADR-0012](ADR-0012-combined-research-scopes-and-context-alignment.md) | Combined Research Scopes and Context Alignment | PROPOSED | Sprint 009 |
| ADR-0004 | Independent Research and Execution Workflows | PLANNED | TBD |
| ADR-0009 | Batch Backtest vs Replay Execution | PLANNED | TBD |
| ADR-0010 | Working Component and Model Fingerprints | PLANNED | TBD |

Market Analysis binding decisions D-001–D-036 remain authoritative in
`docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md`. Sprint 003 materialized the engine subset above as
accepted ADRs.

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

- `docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md`
- `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md`
- `docs/vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md`
- `docs/planning/PROBLEM_REGISTRY.md` — PRB-016
