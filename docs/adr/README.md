# Architectural Decision Records

Catalog of `docs/adr/`. For documentation taxonomy see **[../README.md](../README.md)**.

## Purpose

ADRs preserve **why** significant architectural decisions were made.

Architecture documents describe the current system. ADRs preserve decision history.

## Process

Consolidated here (Sprint 054 T006a) from `docs/vision/WORKFLOWS_AI_ADR.md`
§7.1–7.5, §7.9, §7.10, which previously duplicated — and in places
contradicted — this file. This is now the single authoritative source for
the ADR process; `WORKFLOWS_AI_ADR.md` §7 carries only a pointer to it.

### When an ADR is required

Create an ADR when a decision:

- changes domain boundaries,
- introduces a major abstraction,
- changes dependency direction,
- changes workflow semantics,
- changes public model contracts,
- changes dataset identity or lifecycle,
- changes storage strategy,
- introduces new infrastructure technology,
- introduces distributed processing,
- introduces breaking compatibility,
- resolves a significant architectural disagreement.

Do not create ADRs for trivial implementation details.

### ADR numbering and location

ADRs live in `docs/adr/`, named `ADR-XXXX-slug.md` (or `ADR-MA-XXX-slug.md`
for the Market Analysis engine subset materialized in Sprint 003). ADR
numbers are sequential and immutable. An accepted ADR is not rewritten to
change its recorded history — a changed decision requires a new ADR and a
supersession reference in both directions.

### Review

Every ADR review should verify:

- Does the decision solve a demonstrated problem?
- Does it preserve domain ownership?
- Does it preserve workflow independence?
- Does it preserve reproducibility?
- Does it increase operational complexity?
- Can a simpler option solve the problem?
- Does it affect `user_data` compatibility?
- Does it require migration?
- Is the decision reversible?

### Ownership

An ADR should identify its author, reviewers, affected modules and
implementation status (see Status Model below). AI agents may draft ADRs
and propose a status of `PROPOSED`; they must not silently mark an ADR
`ACCEPTED` without an explicit, direct human approval statement (see
`governance` — no agent approves its own architectural proposal).

## Status Model

```text
PROPOSED    — drafted, awaiting review/approval
ACCEPTED    — approved and binding
PLANNED     — a future ADR is expected for a known decision, not yet written
DEPRECATED  — no longer applies, not formally replaced by another ADR
SUPERSEDED  — replaced by a specific later ADR (cite it)
```

This is the vocabulary actually used across the ADR index below (including
`PLANNED` for ADR-0004/0009/0010/0030) and in real ADR files (e.g.
ADR-0023's "ACCEPTED (§7 amended by ADR-0029)", ADR-0028's
"ACCEPTED — resumed for Sprint 048"). `WORKFLOWS_AI_ADR.md` §7.4 previously
listed a different, mixed-case six-status vocabulary
(`Proposed/Accepted/Rejected/Deferred/Superseded/Deprecated`) that was never
adopted by any ADR in `docs/adr/` — this status model wins because it
matches actual practice, and the vision file's version has been retired
(rejected proposals are simply not merged, and "deferred" architecture
decisions are vision-track content, not an ADR status — see ADR Backlog
below).

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
| [ADR-0031](ADR-0031-predictive-sample-spec-and-task.md) | Predictive Sample Universe (`SampleSpec`) and Research Task Taxonomy (`PredictiveTask`) | PROPOSED | Sprint 056 |
| ADR-0004 | Independent Research and Execution Workflows | PLANNED | TBD |
| ADR-0009 | Batch Backtest vs Replay Execution | PLANNED | TBD |
| ADR-0010 | Working Component and Model Fingerprints | PLANNED | TBD |
| ADR-0030 | Inference-Time Availability Enforcement | PLANNED (conditional on the S049-T001 finding) | TBD |

Market Analysis binding decisions D-001–D-036 remain authoritative in
`docs/vision/MARKET_ANALYSIS_DECISIONS.md` (formerly `MARKET_ANALYSIS_WITH_DECISIONS.md`, dissolved by Sprint 055 T008). Sprint 003 materialized the engine subset above as
accepted ADRs.

## Template

The required sections are `Status`, `Context`, `Decision` and
`Consequences`/`References`. `Alternatives Considered` and `Follow-up` are
optional but common in practice (see ADR-0026, ADR-0028, ADR-0029) — include
them when there were real alternatives or known open follow-on work; omit
them for small, single-option decisions.

```markdown
# ADR-XXXX — Title

## Status

PROPOSED | ACCEPTED | PLANNED | DEPRECATED | SUPERSEDED

## Context

What problem or constraint led to this decision.

## Decision

What was decided.

## Alternatives Considered (optional)

What other options were evaluated, and why they were not chosen.

## Consequences

Positive and negative outcomes of the decision.

## Follow-up (optional)

Known open work this decision creates, if any.

## References

- links to architecture documents, problems, or superseding ADRs
```

This was reconciled (Sprint 054 T006a) against `WORKFLOWS_AI_ADR.md` §7.5's
9-section template (`Rationale`, `Compatibility and Migration`, split
`Positive/Negative/Risks` subsections). That richer template was **not**
adopted by any of the sampled real ADRs (0026–0029 use `Status, Context,
Decision, Alternatives Considered, Consequences, Follow-up, Related`) — this
lean template plus the two optional sections wins because it matches actual
practice rather than an unused proposal.

## ADR Backlog

Decisions that are established architecture but do not yet have an
`ACCEPTED` ADR. Carried over from `WORKFLOWS_AI_ADR.md` §7.6–§7.8 (Sprint 054
T006a) — do not drop silently; either write the ADR or fold the item into an
existing one when picked up.

Already tracked as `PLANNED` in the Index above:

- **ADR-0004** — Independent Research and Execution Workflows
- **ADR-0009** — Batch Backtest vs Replay Execution
- **ADR-0010** — Working Component and Model Fingerprints
- **ADR-0030** — Inference-Time Availability Enforcement (conditional)

Established decisions with no ADR number assigned yet:

- Strategy Composition (`Strategy Model = Market Model × Signal Model ×
  Exit Model × Risk Model`)
- Position Sizing belongs to the Risk Model in Version 1
- `MarketFieldReference` as the only controlled model-expression access to
  market data (no arbitrary DataFrame access)
- Persistent Research Datasets (separating Research Computation from
  Analytics with reusable persisted datasets)
- Hybrid Communication (direct calls for deterministic Research, events for
  Strategy Execution where justified)
- Configuration Boundaries (Pydantic at configuration/validation
  boundaries, not automatically for every domain model)

Deferred until requirements justify them (not rejected — the current
architecture must not depend on these, and no ADR is needed unless a trigger
below fires): distributed Market Analysis Engine, a distributed event broker
(e.g. Kafka), Spark, Kubernetes, microservices, distributed Strategy
Execution, a dedicated feature-store product, an automatic ML feature-vector
layer, a full DOM data model, an options snapshot model, a full order-flow
event model, full event sourcing, a workflow visual DAG editor, a remote
user component registry, a multi-node research scheduler, and a separate
Position Sizing Model.

Reconsideration triggers (write an ADR when one of these fires):

- **Distributed processing** — one machine cannot process required datasets
  in acceptable time; memory limits are repeatedly exceeded; independent
  workloads require horizontal scheduling.
- **Distributed messaging** — event durability exceeds in-memory
  capabilities; multiple independent services consume the same stream;
  partitioned ordering and replay become operational requirements.
- **Microservices** — modules require independent deployment; modules scale
  independently; separate teams own clear bounded contexts; process
  isolation provides measurable value.
- **Feature store** — the same analytical outputs are shared across
  Research and Strategy Execution at significant scale; online/offline
  consistency becomes a demonstrated problem; local Parquet and cache
  solutions are insufficient.
- **Position Sizing Model** — risk budget and sizing require independent
  composition; sizing variants need separate research; execution or
  portfolio requirements justify independent versioning.

## Related Documents

- `docs/vision/PRODUCT_DIRECTION.md` (formerly `ARCHITECTURE_FOUNDATIONS.md`)
- `docs/vision/MARKET_ANALYSIS_DECISIONS.md` (formerly `MARKET_ANALYSIS_WITH_DECISIONS.md`)
- `docs/reference/system/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md`
- `docs/planning/PROBLEM_REGISTRY.md` — PRB-016
