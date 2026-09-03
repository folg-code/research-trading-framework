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
| [ADR-MA-014](ADR-MA-014-marketframe-polars-committed-bulk-engine.md) | MarketFrame and Polars as the Committed Bulk Engine | ACCEPTED | Sprint 036 |
| [ADR-0006](ADR-0006-declarative-market-and-signal-models.md) | Declarative Market and Signal Models | ACCEPTED | Sprint 006 |
| [ADR-0011](ADR-0011-signal-research-outcomes-and-persistence.md) | Signal Research Outcomes and Persistence | ACCEPTED | Sprint 008 |
| [ADR-0012](ADR-0012-combined-research-scopes-and-context-alignment.md) | Combined Research Scopes and Context Alignment | ACCEPTED | Sprint 009 |
| [ADR-0013](ADR-0013-signal-research-analytics-boundary.md) | Signal Research Analytics Boundary | ACCEPTED | Sprint 010 |
| [ADR-0014](ADR-0014-historical-archive-import-and-market-trade-storage.md) | Historical Archive Import and MarketTrade Partitioned Storage | ACCEPTED | Sprint 011 |
| [ADR-0015](ADR-0015-derived-ohlcv-from-trades.md) | Derived OHLCV from Published Trades | ACCEPTED | Sprint 012 |
| [ADR-0016](ADR-0016-ohlcv-strategy-research-mvp.md) | OHLCV Strategy Research MVP | ACCEPTED | Sprint 013 |
| [ADR-0017](ADR-0017-strategy-research-inspection-boundary.md) | Strategy Research Inspection Boundary | ACCEPTED | Sprint 014 |
| [ADR-0018](ADR-0018-continuous-futures-materialization.md) | Continuous Futures Materialization | ACCEPTED | Sprint 015 |
| [ADR-0019](ADR-0019-robustness-research-mvp.md) | Robustness Research MVP | ACCEPTED | Sprint 016 |
| [ADR-0020](ADR-0020-model-research-methodology-mvp.md) | Model Research Methodology MVP | ACCEPTED | Sprint 017 |
| [ADR-0021](ADR-0021-live-dry-run-execution-demo.md) | Live Dry-Run Execution Demo | ACCEPTED | Sprint 018 |
| [ADR-0022](ADR-0022-repository-top-level-layout.md) | Repository Top-Level Layout | ACCEPTED | Sprint 029 |
| [ADR-0023](ADR-0023-predictive-research-boundary.md) | Predictive Research Domain Boundary | ACCEPTED (§7 amended by ADR-0029) | Sprint 039 |
| [ADR-0024](ADR-0024-machine-learned-state-promotion.md) | Promotion Conditions for Machine-Learned Market Analysis States | ACCEPTED | Sprint 044 |
| [ADR-0025](ADR-0025-binance-usdm-historical-klines-import.md) | Binance USD-M Historical Klines Import | ACCEPTED | Sprint 045 |
| [ADR-0026](ADR-0026-operator-cli-framework-and-placement.md) | Operator CLI: Framework, Placement and Config Contract | ACCEPTED | Sprint 046 |
| [ADR-0027](ADR-0027-operator-authored-strategy-loading.md) | Operator-Authored Strategy Loading (`strategy_file` + `build_strategy()`) | ACCEPTED | Sprint 047 |
| [ADR-0028](ADR-0028-bracket-exit-and-equity-relative-sizing.md) | Bracket Exits and Equity-Relative Sizing: Widening the Strategy Model Gate | ACCEPTED (declined for Sprint 047; resumed with corrections for Sprint 048) | Sprint 047 / 048 |
| [ADR-0029](ADR-0029-promoted-predictive-artifact.md) | Promoted Predictive Artifact: Parameter Format, Promotion Store, and the Narrow ADR-0023 §7 Amendment | ACCEPTED | Sprint 049 |
| ADR-0004 | Independent Research and Execution Workflows | PLANNED | TBD |
| ADR-0009 | Batch Backtest vs Replay Execution | PLANNED | TBD |
| ADR-0010 | Working Component and Model Fingerprints | PLANNED | TBD |
| ADR-0030 | Inference-Time Availability Enforcement | PLANNED (conditional on the S049-T001 finding) | TBD |

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

- `docs/vision/ARCHITECTURE_FOUNDATIONS.md`
- `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md`
- `docs/vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md`
- `docs/planning/PROBLEM_REGISTRY.md` — PRB-016
