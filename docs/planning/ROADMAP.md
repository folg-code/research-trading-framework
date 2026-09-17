# Roadmap

Status: **ACCEPTED**. Reviewed against [Current Status](CURRENT_STATUS.md) on 2026-09-11. This page is the phase index and dependency map; detailed plans live in `roadmap/`, completed sprint evidence in the [Archive](../archive/README.md), and implemented behavior in [Reference](../reference/README.md).

## Direction

Build small vertical slices in a modular monolith. Published market facts feed reusable Market Analysis, declarative models, independent research workflows and a separately bounded execution runtime. Preserve reproducibility, temporal correctness, domain ownership and the `src/`–`user_data/` boundary. See [Product Direction](../vision/PRODUCT_DIRECTION.md) and [cross-phase gates](roadmap/CROSS_PHASE_STANDARDS_AND_GATES.md).

## Capability tracks and phase index

| Track / phase | Status at last review | Detail |
|---|---|---|
| 0–1 Governance and repository foundation | Complete | [Completed phases](../archive/planning/ROADMAP_COMPLETED_PHASES.md) |
| 2A OHLCV Market Data | Complete | [Market Data phase family](roadmap/PHASE_02_MARKET_DATA.md) |
| 2B/2C Historical import, trades and continuous futures | Partly complete; further slices planned | [Market Data phase family](roadmap/PHASE_02_MARKET_DATA.md) |
| 2D Options snapshots | Planned | [Market Data phase family](roadmap/PHASE_02_MARKET_DATA.md) |
| 2E Paid live Market Data | Gated | [Market Data phase family](roadmap/PHASE_02_MARKET_DATA.md) |
| 2F Exchange REST historical import | Complete | [Completed phases](../archive/planning/ROADMAP_COMPLETED_PHASES.md) |
| 3 Market Analysis MVP, 4A bar/MTF | Complete | [Market Analysis phase family](roadmap/PHASE_04_MARKET_ANALYSIS.md) |
| 4B Orderflow, 4C options-derived analysis | Planned | [Market Analysis phase family](roadmap/PHASE_04_MARKET_ANALYSIS.md) |
| 5 Signal and Model Research | Complete | [Completed phases](../archive/planning/ROADMAP_COMPLETED_PHASES.md) |
| 6A OHLCV Strategy Research | Complete | [Completed phases](../archive/planning/ROADMAP_COMPLETED_PHASES.md) |
| 6B Multi-data Strategy Research | Planned | [Phase 6B](roadmap/PHASE_06B_MULTI_DATA_STRATEGY.md) |
| 7 Robustness Research | Complete | [Completed phases](../archive/planning/ROADMAP_COMPLETED_PHASES.md) |
| 8A BTC futures dry-run slice | Built; Sprint 062 deployment task remains | [Current Status](CURRENT_STATUS.md) |
| 8 Replay and Paper Execution expansion | Planned | [Phase 8](roadmap/PHASE_08_REPLAY_AND_PAPER.md) |
| 9 Live and multi-account execution | Planned | [Phase 9](roadmap/PHASE_09_LIVE_AND_MULTI_ACCOUNT.md) |
| 10A–10C Predictive Research | Complete | [Completed phases](../archive/planning/ROADMAP_COMPLETED_PHASES.md) |
| 11 Operator CLI, 12 Strategy Authoring, 13 Exit/Risk | Complete | [Completed phases](../archive/planning/ROADMAP_COMPLETED_PHASES.md) |
| 14A Predictive artifact promotion | Complete; 14B not planned | [Phase 14](roadmap/PHASE_14_PREDICTIVE_PROMOTION.md) |
| 15 Predictive catalog and real-data study | Complete | [Phase 15](roadmap/PHASE_15_PREDICTIVE_CATALOG.md) |
| 16 Quant Research Workbench | Active: 16A–16C complete, 16D in progress | [Phase 16](roadmap/PHASE_16_QUANT_WORKBENCH.md), [16D dashboard](roadmap/PHASE_16D_PORTFOLIO_DASHBOARD.md) |
| 17 Research Application (Local Workbench) | Active: architecture triage complete (ADR-0037–0042); Sprint 064 approved and open | [Phase 17](roadmap/PHASE_17_RESEARCH_APPLICATION.md) |

A completed phase remains in the index for orientation, not as an instruction to reread its delivery history. The [archive phase index](../archive/README.md) locates each completed sprint and its companion artifacts.

## Cross-track dependencies

```text
2A Market bars ──┬── 5 Signal Research
                 └── 6A Strategy Research
2C Trades ───────→ 4B Orderflow Analysis ──→ 6B Multi-data Strategy Research
2D Options ──────→ 4C Options Analysis ────→ 6B Multi-data Strategy Research
4A Market Analysis + 5 Signal Research ───→ 10 Predictive Research
```

Phase 16 consumes existing research runners and the common analytical catalog. Phase 14B does not open automatically after 14A. A positive backtest alone does not open the paid live-data gate. See [research data strategy](roadmap/RESEARCH_DATA_STRATEGY.md) and [cross-phase standards and gates](roadmap/CROSS_PHASE_STANDARDS_AND_GATES.md).

Phase 17 is a separate product surface, not a Phase 16 increment: it is the private local operator control plane (`apps/workbench`) over existing Market Data and Signal Research workflows, defined by `docs/vision/RESEARCH_APPLICATION_PRODUCT_VISION.md` and `docs/product/PRD-research-workbench-mvp.md`, independent of Phase 16E–16G. It does not depend on 16D or later Phase 16 increments, but is sequenced after Sprint 062/T007 closes so the maintainer is not running a live VPS deploy and opening a new application surface at the same time.

## Terminology follow-up increments

The two Terminology Foundation waves establish product and reference language
without changing technical identities or persisted artifacts. Their scope and
compatibility boundary are fixed by the [Terminology Foundation PRD](../product/PRD-terminology-foundation.md)
and [ADR-0045](../adr/ADR-0045-layered-research-terminology.md). The following
directions do not hold up the foundation's final integration to `main` and do
not authorize implementation on their own.

| Direction | Outcome and completion signal | Dependency or gate |
|---|---|---|
| Typed Research Catalog — separate, unplanned increment | Applicable private Workbench and public dashboard catalog views use explicit, qualified research subjects (Market Model, Signal Model or Estimator) rather than a bare `model` inferred from a title. Missing or legacy subject evidence stays visibly unclassified; existing artifacts and identities remain readable. | Establish the owning persisted source of subject identity; review [ADR-0042](../adr/ADR-0042-workbench-catalog-index-and-comparison-facts.md)'s manifest-as-truth index and framework-owned comparison facts, plus [ADR-0034](../adr/ADR-0034-portfolio-publication-boundary.md)/[ADR-0035](../adr/ADR-0035-complete-public-catalog-publication.md)'s deny-by-default public projection and immutable release. Approve any new or versioned presentation contract and public allowlist separately, before expanding the Phase 17D catalog/comparison surface or changing the public `model` filter. |
| Code-contract terminology — conditional, not scheduled | Consider `ExitModel`, `RiskModel` or `StrategyModelDefinition` aliases or renames only if concrete user or integration friction remains after explanatory copy adopts Exit Policy, Risk Policy and Strategy Definition. | A separate contract decision must define versioning, compatibility readers or aliases, and deprecation policy. No automatic follow-on from ADR-0045. |

Historical schema and storage renames, including
`user_data/research/market_research/`, are not planned. Reconsider them only
for a demonstrated need with an approved migration and preservation of
historical hashes and evidence. The main Typed Research Catalog risks are
ambiguous legacy manifests, inconsistent private/public subject typing,
accidental identity or artifact migration, and leakage through the public
projection. Neither direction introduces a shared framework-level Study
aggregate or inferred cross-workflow lineage.

## Deferred directions

Microservices, distributed processing, a dedicated feature store, full event sourcing, full DOM as primary storage and automated feature-engineering search remain deferred until a demonstrated need and architecture decision justify them. The full recorded list and gates are in [Cross-Phase Standards and Gates](roadmap/CROSS_PHASE_STANDARDS_AND_GATES.md); future designs belong in [Vision](../vision/README.md).

## Review rule

Update phase status here after a material phase change. Keep task progress in active sprint files, accepted decision rationale in ADRs, current system behavior in Reference and completed outcomes in the Archive. The [pre-restructuring roadmap snapshot](../archive/snapshots/ROADMAP_2026-09-11.md) preserves older wording and section numbers for historical references.

## Earlier section references

Older documents cite `ROADMAP.md` by section number. Use this map without loading the entire historical snapshot:

| Former section | Current destination |
|---|---|
| §6, §8 | [Market Data](roadmap/PHASE_02_MARKET_DATA.md), [Market Analysis](roadmap/PHASE_04_MARKET_ANALYSIS.md) |
| §10, §12, §13 | [Phase 6B](roadmap/PHASE_06B_MULTI_DATA_STRATEGY.md), [Phase 8](roadmap/PHASE_08_REPLAY_AND_PAPER.md), [Phase 9](roadmap/PHASE_09_LIVE_AND_MULTI_ACCOUNT.md) |
| §13F, §13G, §13H | [Phase 14](roadmap/PHASE_14_PREDICTIVE_PROMOTION.md), [Phase 15](roadmap/PHASE_15_PREDICTIVE_CATALOG.md), [Phase 16](roadmap/PHASE_16_QUANT_WORKBENCH.md) |
| §14–§17 | [Research Data Strategy](roadmap/RESEARCH_DATA_STRATEGY.md), [Standards and Gates](roadmap/CROSS_PHASE_STANDARDS_AND_GATES.md) |
