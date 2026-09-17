# Market Analysis — Future Direction

Current component identity, dependency planning, batch multitimeframe computation and alignment are in [Market Analysis Architecture](../reference/system/MARKET_ANALYSIS_ARCHITECTURE.md), [Time and Alignment](../reference/system/TIME_AND_ALIGNMENT.md) and the [module guide](../reference/modules/MARKET_ANALYSIS.md). This page retains only proposed extensions. The [pre-review snapshot](../archive/snapshots/MARKET_ANALYSIS_FUTURE_pre_review.md) preserves the earlier mixed classification detail.

## Component Catalog Expansion (captured 2026-09-17)

```text
Status: DRAFT — maintainer intent captured 2026-09-17; PRD scope not approved
Scope: a coordinated set of new market_analysis components, gathered here as
       one input to a future PRD before implementation begins
```

This section consolidates five idea-inbox entries produced from a review of
an external, prior framework's feature catalogs (analyzed 2026-09-17,
mechanism-only inspiration — no code or naming carried over; see each idea
for full source discussion) into one place, so a future PRD has a single
starting point instead of five scattered registry entries. It is not itself
a PRD, an architecture decision or a sprint. The "State families" section
above already names candidate future State categories (trend, volatility
regime, momentum, liquidity, structural condition, market phase) at a
conceptual level; this section is the concrete component-level proposal
that would populate several of those categories.

### Proposed component packs

| Idea | Pack | Components (count) |
|---|---|---|
| [IDEA-027](../planning/registries/idea-market-analysis.md#idea-027) | Price-Structure and Session Context | `structure.range_discontinuity`, `structure.impulse_origin_range`, `structure.level_sweep_rejection`, `structure.level_role_reversal`, `structure.matched_extreme_pair`, `structure.close_reversal_level`, `structure.impulse_follow_through`, `structure.opening_gap`, `session.overlap_window`, `session.previous_period_extreme`, `session.current_period_extreme` (11) |
| [IDEA-028](../planning/registries/idea-market-analysis.md#idea-028) | Volatility Estimators | `volatility.range_based_variance`, `volatility.directional_asymmetry`, `volatility.acceleration`, `volatility.choppiness_index`, `volatility.regime_state` (5) |
| [IDEA-029](../planning/registries/idea-market-analysis.md#idea-029) | Trend and Momentum Efficiency | `trend.movement_efficiency`, `trend.normalized_slope`, `momentum.normalized_rate_of_change` (3) |
| [IDEA-030](../planning/registries/idea-market-analysis.md#idea-030) | Rolling Window Position | `statistics.rolling_window_position`, a generic component-composing-component utility (1) |
| [IDEA-031](../planning/registries/idea-market-analysis.md#idea-031) | Candle Pattern and Bar-Volume | `candle.reversal_pattern`, `candle.smoothed_ohlc`, `volume.rolling_weighted_price`, `volume.cumulative_trend` (4) |
| [IDEA-032](../planning/registries/idea-market-analysis.md#idea-032) | Level Distance Extension and Fibonacci Levels | extends existing `structure.level_distance`; adds `structure.fibonacci_retracement_level`, `structure.fibonacci_extension_level` (2 new + 1 extension) |

26 new components and one extension of an existing one, across five idea
entries, none yet approved for implementation.

### Naming convention (governs all five packs)

Set in full in [IDEA-027](../planning/registries/idea-market-analysis.md#idea-027):
names describe the calculation or observed fact, never a trading metaphor;
a source-material abbreviation may appear once in prose, never as a field
or component name; invalidation/variant states are fields on one component,
not separate components; clarity outweighs brevity; every component gets a
[`ANALYSIS_COMPONENT_CATALOG.md`](../reference/modules/ANALYSIS_COMPONENT_CATALOG.md)
entry before promotion. IDEA-032's Fibonacci naming is the one deliberate
exception — a standard mathematical term, not trading slang.

### Cross-pack dependencies

- **IDEA-029** needs a single shared volatility normalizer decided once
  (the existing `volatility.relative_volatility` or IDEA-028's new
  `volatility.range_based_variance`) — not per-component.
- **IDEA-030** likely has the largest prerequisite: whether the registry
  already supports a component consuming another component's `OutputRef`
  as input, or whether that capability must be built first. This affects
  every future `*_state` classifier, not just this idea.
- **IDEA-032** is best sequenced after IDEA-027's `structure.matched_extreme_pair`
  and `session.previous_period_extreme` exist, since part of its work is
  wiring those in as additional level sources for `structure.level_distance`.
- **IDEA-031**'s session-anchored VWAP variant (left out of its initial
  scope) would depend on IDEA-027's session-calendar placement decision.

### Related planning artifacts

- Validation of implemented components (per-component via Signal Research,
  per-strategy via a hand-frozen Strategy Research case list) is planned as
  IDEA-027's "Validation Approach" section — not yet a numbered sprint, and
  explicitly not dependent on Strategy Research family/sweep machinery
  (`PRB-020`, Phase 16E, directional/unplanned).
- [Phase 18](../planning/roadmap/PHASE_18_DASHBOARD_RESEARCH_EVIDENCE.md)
  (dashboard research evidence views) is a downstream consumer of whatever
  this expansion's validation series produces — not a dependency of the
  expansion itself.
- [IDEA-010](../planning/registries/idea-market-analysis.md#idea-010)
  (Component Scaffolding CLI) and
  [IDEA-011](../planning/registries/idea-market-analysis.md#idea-011)
  (Automatic Candidate Promotion Report) are tooling ideas that would
  reduce the manual registration friction (a component today needs a
  hand-written `register_<name>_component` function wired into
  `register_mvp_components`) every one of these 26 components would
  otherwise hit individually.

### Questions for the future PRD

- Which pack, or which subset of one pack, forms the first bounded
  implementation slice? IDEA-027 was the original review's starting point
  and has the most self-contained candidates
  (`structure.range_discontinuity`, `structure.impulse_origin_range`), but
  the PRD should decide this explicitly rather than default to entry order.
- Does IDEA-030's composition-capability question block any `*_state`
  work across all five packs, or only the specific components that name it
  as a dependency?
- Should component-registration friction (IDEA-010/011) be resolved before
  or alongside the first pack's implementation, given 26 components will
  otherwise repeat the same manual registration step individually?
- What promotion criteria are common across all five packs versus specific
  to one (e.g. IDEA-027's causal-only acceptance gate for `session.*`
  components does not obviously generalize to IDEA-028's volatility
  estimators)?

This section records future direction. It does not approve a PRD,
architecture change, sprint or implementation. For current component
behavior, use [Market Analysis](../reference/modules/MARKET_ANALYSIS.md)
and the [component catalog](../reference/modules/ANALYSIS_COMPONENT_CATALOG.md).

## State families

Reusable States can classify conditions built from market facts, Features and Structures, independent of a specific strategy. Candidate families include trend, volatility regime, momentum, liquidity, structural condition and market phase. These names describe a possible taxonomy, not a promise of matching current classes or a separate State output type.

## Explicit intrabar semantics

Partial higher-timeframe input should be available only through an explicit intrabar contract. It would declare update frequency, availability time, output stability, cache identity and research/runtime parity assumptions. Ordinary resampling must not accidentally expose an incomplete bar as a closed-bar value.

## Derived resampling datasets

If resampled data is published as a reusable dataset, its lineage should identify source dataset and version, source/target timeframe, boundary rules, calendar version, resampling policy and checksum where appropriate. The exact user-workspace layout is not set by this proposal; use [User Workspace](../reference/system/USER_WORKSPACE.md) for the current layout.

## Workspace lifecycle and column pruning

The current executor keeps required analytical results for one plan. A future
dependency-liveness policy could release an intermediate after its consumers
finish, provided it is neither a requested final output nor retained by a
declared cache policy. Dependency-consumer counts, view requests and lineage
must make that choice explicit. General column pruning should remove
unneeded physical columns without changing result identity, availability or
reproducibility. These are optimizations to design and test, not current
workspace behavior.

A generic persisted `DerivedAnalysisDataset` is also future work. If research
reuse justifies it, the artifact would identify its source `DatasetRef`,
requested outputs, computation and implementation identities, parameters,
alignment and assembly policy, plus lineage and retention. It must remain
separate from canonical Market Data rather than silently publishing analysis
outputs as market facts.

## Richer component request

A future explicit request shape may name source, computation and evaluation timeframes plus resampling/alignment policies. Today's `ComponentRequest` and `ResolvedComponentRequest` are different, narrower contracts; see [ADR-MA-012](../adr/ADR-MA-012-batch-multitimeframe-computation-with-polars.md). Decorator syntax, if offered, must produce an explicit serializable request and must not hide dependencies, warm-up, availability or lineage.

Future computation identity may also need explicit resampling policy,
alignment policy and calendar version alongside component identity, parameters,
instrument, source dataset and timeframes. The exact key must be justified by
current consumers and cannot be inferred from the older 11-field proposal.
