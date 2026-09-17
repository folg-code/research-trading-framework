# Phase 19 — Market Analysis Component Catalog Expansion (2026-09 Batch)

```text
Status: APPROVED (maintainer, 2026-09-17). Wave 0 COMPLETE — all decisions
ACCEPTED (maintainer, 2026-09-17). Sprint 065 (Tooling) CLOSED and merged
to main (#552-#556). Sprint 066 (Wave A, 20 components) CLOSED and
merged to main (#557-#566). Sprint 067 (Wave B, 6 components) OPEN.
```

**Product source:** [`docs/product/PRD-market-analysis-catalog-expansion-2026-09.md`](../../product/PRD-market-analysis-catalog-expansion-2026-09.md)
— the maintainer's grill-me discovery record; authoritative on scope,
non-goals and success metrics. Consolidated from
[`docs/vision/MARKET_ANALYSIS_FUTURE.md`](../../vision/MARKET_ANALYSIS_FUTURE.md)
§"Component Catalog Expansion" and five idea-inbox entries
([IDEA-027](../registries/idea-market-analysis.md#idea-027)–[IDEA-032](../registries/idea-market-analysis.md#idea-032)),
plus tooling ideas
[IDEA-010](../registries/idea-market-analysis.md#idea-010)/[IDEA-011](../registries/idea-market-analysis.md#idea-011).

**Wave 0 decisions:** [PHASE_19_WAVE0_DECISIONS.md](PHASE_19_WAVE0_DECISIONS.md)
— all six decisions (D-P19-01 through D-P19-06) **ACCEPTED (maintainer,
2026-09-17)**, binding for implementation.

**Priority:** maintainer-stated highest priority among currently unapproved
tracks — sequenced ahead of other not-yet-approved PRDs.

## Purpose

Grow the Market Analysis component catalog from its current thin state (no
session-context, no price-structure-zone components, one volatility-state
classifier, no volatility-normalized trend/momentum measures, no
candle-pattern or bar-volume components, single-source `structure.level_distance`)
by implementing 26 new components plus one new multi-level-source component
(`structure.distance_to_level`, replacing the originally-proposed
in-place `structure.level_distance` extension — D-P19-03), identified from a
2026-09-17 review of an external framework's feature catalog
(mechanism-only inspiration, no code/naming carried over). Scope and
acceptance criteria are fixed by the PRD; sequencing and design decisions
are fixed by the accepted Wave 0 decision set; this file tracks phase-level
status and sprint structure.

## Sprint plan (accepted, per D-P19-06)

Three sprints, all now opened and numbered:

| Sprint | Scope | State |
|---|---|---|
| **Sprint 065 — Tooling** | [IDEA-010](../registries/idea-market-analysis.md#idea-010) Component Scaffolding CLI (`scripts/market_analysis/scaffold_component.py`) + [IDEA-011](../registries/idea-market-analysis.md#idea-011) Promotion Readiness Report (`scripts/market_analysis/check_promotion_readiness.py`), piloted against `structure.opening_gap` | **Closed, merged to main** — T001-T005 done, see [SPRINT_065.md](../sprints/SPRINT_065.md) |
| **Sprint 066 — Wave A (20 remaining components)** | [IDEA-027](../registries/idea-market-analysis.md#idea-027) (10 remaining `structure.*`/`session.*` — `structure.opening_gap` already delivered as Sprint 065's pilot), [IDEA-028](../registries/idea-market-analysis.md#idea-028) (5 `volatility.*`), [IDEA-031](../registries/idea-market-analysis.md#idea-031) base components (`candle.reversal_pattern`, `candle.smoothed_ohlc`, `volume.rolling_weighted_price` fixed-window, `volume.cumulative_trend`), [IDEA-030](../registries/idea-market-analysis.md#idea-030) (`statistics.rolling_window_position`) — built in parallel, using Sprint 065's tooling | **Closed, merged to main** — all 20 components done, T001-T009, see [SPRINT_066.md](../sprints/SPRINT_066.md) (Closeout) |
| **Sprint 067 — Wave B (6 components)** | [IDEA-029](../registries/idea-market-analysis.md#idea-029) (`trend.normalized_slope`, `momentum.normalized_rate_of_change`, normalized against `volatility.relative_volatility.value` per D-P19-02), [IDEA-032](../registries/idea-market-analysis.md#idea-032) (`structure.distance_to_level` + two Fibonacci-level components, per D-P19-03), [IDEA-031](../registries/idea-market-analysis.md#idea-031)'s deferred session-anchored VWAP variant | **Open** — see [SPRINT_067.md](../sprints/SPRINT_067.md) |

Opening any of these as a numbered sprint is a separate governance gate
from this phase's approval and from Wave 0's acceptance — it requires its
own explicit go-ahead.

## Key accepted design decisions (see Wave 0 doc for full reasoning)

- **IDEA-030 unblocked**: the registry already supports a component
  consuming another component's `OutputRef` via
  `ComponentDependency`/`ComponentOutputRef`
  (`structure.level_distance`, `trend.ema_distance`, `momentum.macd`
  already do this) — no new registry capability needed.
- **IDEA-032 is a new component**, `structure.distance_to_level`, not an
  in-place extension of `structure.level_distance` (whose `OutputSchema`
  is a fixed, hardcoded-to-one-source shape that cannot generalize
  without breaking existing consumers). `structure.level_distance` is
  left untouched.
- **IDEA-029's shared normalizer** is the existing
  `volatility.relative_volatility.value` (not the new
  `volatility.range_based_variance`) — estimator-family consistency with
  the close-to-close trend/momentum measures being normalized.
- **Session-hour definitions** (Asia/London/New York) live in the shared
  `src/trading_framework/time/sessions/` module, extending the existing
  `TradingSessionResolver` pattern (`CmeEsRthSessionResolver` precedent) —
  not duplicated inside IDEA-027's component pack.
- **`candle.reversal_pattern`** gets a 4-pattern prioritized rule set
  (`engulfing` → `level_close_reversal` → `rejection_wick` → `none`).
- **Starting ATR-multiple defaults**: `structure.impulse_origin_range`
  `impulse_atr_multiple = 1.5`; `structure.range_discontinuity`
  `min_gap_atr_multiple = 0.1` — both calibratable parameters, not fixed
  constants.
- **No MTF variants** for any of the 27 components in this phase —
  precedent (single-timeframe first) applies uniformly, no exceptions.
- **Promotion criteria** split catalog-wide (naming convention, contract
  test, catalog entry, dependency-declaration correctness) vs.
  pack-specific (causal-only gate for `session.*` only; ATR-threshold
  calibration for the specific components that have one; normalizer
  consistency for IDEA-029 only).

## Binding rules for the whole phase

- Naming convention from [IDEA-027](../registries/idea-market-analysis.md#idea-027)
  governs every pack: names describe the calculation or observed fact, never
  a trading metaphor (source-material abbreviations may appear once in
  prose only); invalidation/variant states are fields, not separate
  components; IDEA-032's "Fibonacci" naming is the one deliberate exception.
- Every component gets an [`ANALYSIS_COMPONENT_CATALOG.md`](../../reference/modules/ANALYSIS_COMPONENT_CATALOG.md)
  entry (formula, warm-up, zero-denominator convention) before promotion.
- All `session.*` components are causal-only from the first implementation —
  a hard acceptance gate, not a later fix.
- "Done" for this phase is implementation-only: components run error-free
  and produce their documented output shape. Signal Research / Strategy
  Research validation of the new components is explicitly out of scope
  (PRD non-goals) and would open as a separate, later, numbered sprint.
- No ADR is expected for this phase (precedent: Sprint 047/048/051
  component additions needed none; Wave 0 confirmed no registry structural
  change is required).

## Dependencies

- None on Phase 16E (Strategy Families/PRB-020) or Phase 18 (dashboard
  evidence views) — both are downstream, independent of this phase.
- [Phase 18](PHASE_18_DASHBOARD_RESEARCH_EVIDENCE.md)'s 18A increment is a
  future consumer of whatever this phase's (separately-scoped, not-yet-open)
  validation series eventually produces — not a dependency of this phase.

## Review rule

Update this file's sprint states after a material decision (a sprint
opening, scope narrowed by the maintainer). Keep the source of truth for
*why* a decision was made in the PRD or the Wave 0 decisions doc, not here.
