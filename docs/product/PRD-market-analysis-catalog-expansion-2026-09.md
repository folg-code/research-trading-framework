# PRD — Market Analysis Component Catalog Expansion (2026-09 Batch)

```text
Status: APPROVED (maintainer, 2026-09-17)
```

Feature-level PRD within the existing Trading Research Framework product,
following the grill-me discovery pattern established for Phase 2F/11/12/13,
the ML runtime-promotion track and `docs/product/PRD-predictive-research-catalog-expansion.md`.
This is the maintainer's stated **highest priority** among currently
unapproved tracks — sequenced ahead of any other not-yet-approved PRD.

Source input: [`docs/vision/MARKET_ANALYSIS_FUTURE.md`](../vision/MARKET_ANALYSIS_FUTURE.md)
§"Component Catalog Expansion (captured 2026-09-17)", which consolidated
five idea-inbox entries into one starting point for this PRD. This document
is that PRD.

## Problem

The Market Analysis component catalog is thin relative to the vocabulary a
Signal Model or a `PredictiveStudySpec` `FeatureSpec` can draw from today —
no session-context components, no price-structure-zone components, only one
volatility-state classifier, no volatility-normalized trend/momentum
measures, no candle-pattern or bar-volume components, and only a single-level
version of `structure.level_distance`.

A 2026-09-17 review of an external, prior framework's feature catalog
(mechanism-only inspiration — no code or naming carried over) surfaced 26
concrete candidate components plus one extension of an existing component,
captured as five idea-inbox entries
([IDEA-027](../planning/registries/idea-market-analysis.md#idea-027)–[IDEA-032](../planning/registries/idea-market-analysis.md#idea-032))
and consolidated in the vision doc above. Left as five scattered registry
entries, none of them would get scoped as implementation work, and 26
components registered one at a time would each hit the same manual
`register_<name>_component` / `register_mvp_components` friction the
maintainer has already flagged as worth fixing
([IDEA-010](../planning/registries/idea-market-analysis.md#idea-010),
[IDEA-011](../planning/registries/idea-market-analysis.md#idea-011)).

## Goals (v1)

- **Full scope: all six ideas.** Implement all 26 proposed components plus
  IDEA-032's multi-level-source work (scoped as a new component — see
  below, not the in-place `structure.level_distance` extension originally
  proposed)
  ([IDEA-027](../planning/registries/idea-market-analysis.md#idea-027)
  through [IDEA-032](../planning/registries/idea-market-analysis.md#idea-032)),
  through the existing `model_authoring` DSL / registry / NumPy-implementation
  pattern (precedent: `candle.wick`, `structure.level_distance`,
  `trend.ema_distance`, `volatility.range_expansion` — none of these needed
  a dedicated ADR).
- **Registration tooling first, as a prerequisite.** Build
  [IDEA-010](../planning/registries/idea-market-analysis.md#idea-010)
  (Component Scaffolding CLI) and
  [IDEA-011](../planning/registries/idea-market-analysis.md#idea-011)
  (Automatic Candidate Promotion Report) before or alongside the first wave
  of components — not after — so the other 20+ components in this PRD don't
  each repeat today's fully manual registration step.
- **Two-wave sequencing by structural complexity, not by idea-inbox order:**
  - **Wave A — simple/independent components, built in parallel.** No
    cross-pack blocking dependency: all of
    [IDEA-027](../planning/registries/idea-market-analysis.md#idea-027)'s
    11 `structure.*`/`session.*` components,
    [IDEA-028](../planning/registries/idea-market-analysis.md#idea-028)'s
    5 `volatility.*` estimators,
    [IDEA-031](../planning/registries/idea-market-analysis.md#idea-031)'s
    `candle.reversal_pattern`, `candle.smoothed_ohlc`,
    `volume.rolling_weighted_price` (fixed-window variant only),
    `volume.cumulative_trend`, and
    [IDEA-030](../planning/registries/idea-market-analysis.md#idea-030)'s
    `statistics.rolling_window_position`. **Wave 0 confirmed (2026-09-17)
    that the registry already supports a component consuming another
    component's `OutputRef` as input** (`structure.level_distance`,
    `trend.ema_distance` and `momentum.macd` already use this pattern via
    `ComponentDependency`/`ComponentOutputRef`,
    `src/trading_framework/market_analysis/models/dependencies.py:26-33`) —
    IDEA-030 is **not blocked** and moves into Wave A as an ordinary
    component, not a separate investigation track.
  - **Wave B — composed/dependent components, built after Wave A lands.**
    [IDEA-029](../planning/registries/idea-market-analysis.md#idea-029)
    (needs a shared volatility normalizer decided once — architect's call
    in Wave 0, see Open questions),
    [IDEA-032](../planning/registries/idea-market-analysis.md#idea-032)
    (see below — now scoped as a **new** component, not an extension, using
    Wave A's `structure.matched_extreme_pair` and
    `session.previous_period_extreme` as level sources, plus the two new
    Fibonacci-level components), and
    [IDEA-031](../planning/registries/idea-market-analysis.md#idea-031)'s
    deferred session-anchored VWAP variant (needs Wave A's session-calendar
    placement decision).
- **IDEA-032 is a new component, not an in-place extension of
  `structure.level_distance`.** Wave 0 found `structure.level_distance`'s
  `OutputSchema` is a fixed two-field shape
  (`distance_to_session_high_atr`/`distance_to_session_low_atr`,
  `src/trading_framework/market_analysis/components/structure/level_distance.py:61-66`)
  hardcoded to one level source
  (`structure.session_range`, same file:49,120-132). Adding simultaneous
  level sources (previous-period extreme, matched-extreme-pair) cannot be
  additive against that schema without breaking existing consumers.
  Maintainer decision (2026-09-17): build a new, generic component (e.g. a
  "distance-to-any-level" shape, exact name to be set per the naming
  convention) instead of modifying `structure.level_distance` in place. The
  existing component is left untouched — no breaking change, no consumer
  migration.
- **Naming convention governs all packs**, set in full in
  [IDEA-027](../planning/registries/idea-market-analysis.md#idea-027):
  names describe the calculation or observed fact, never a trading
  metaphor; a source-material abbreviation may appear once in prose, never
  as a field or component name; invalidation/variant states are fields on
  one component, not separate components; IDEA-032's "Fibonacci" naming is
  the one deliberate exception (standard mathematical term). Every
  component gets a
  [`ANALYSIS_COMPONENT_CATALOG.md`](../reference/modules/ANALYSIS_COMPONENT_CATALOG.md)
  entry (formula, warm-up, zero-denominator convention) before promotion.
- **`session.*` components are causal-only from the first implementation** —
  a hard acceptance gate carried over from IDEA-027, not a later fix. No
  full-period high/low may be assigned to bars before that period closes.

## Non-goals (v1)

- **Validation of the new components.** "Done" for this PRD is: each
  component is implemented, registered, has a passing component-contract
  test, and demonstrably runs end-to-end (no errors) producing the expected
  output shape through at least one example composition. Signal Research
  (per-component) and hand-frozen Strategy Research (per-strategy)
  validation — described in IDEA-027's "Validation Approach" — and any
  analysis of research results are explicitly **out of scope**, to be
  opened as a separate, later, numbered sprint once a maintainer sets the
  concrete case list.
- **Strategy Research family/sweep machinery** (`PRB-020`, Phase 16E). Not
  needed for this PRD's scope and not built as a side effect of it.
- **Order-flow or tick/trade/quote-derived components**
  ([IDEA-012](../planning/registries/idea-market-analysis.md#idea-012) and
  related) — `volume.*` components in this PRD use only per-bar OHLCV
  volume, already available.
- **Reopening CI policy or any synthetic-vs-real-data question** — this PRD
  is pure component-catalog work; it does not touch ADR-0023 §8 or any
  Predictive Research pipeline.
- **Dashboard or reporting surfaces for the new components** — Phase 18
  (dashboard research evidence views) is a downstream, independent consumer
  of whatever a future validation series produces, not a dependency or
  deliverable of this PRD.
- **MTF (multi-timeframe) variants of the new components from day one** —
  precedent (`volatility.atr`, `trend.slope`) is single-timeframe first,
  MTF projection later; architect confirms this still applies per
  component in Wave 0 rather than building MTF variants speculatively.

## Success metrics

1. **Registration tooling exists and is used.** IDEA-010's scaffolding CLI
   and/or IDEA-011's promotion report are in place before Wave A's
   components are registered, and Wave A actually uses them (not built and
   left unused).
2. **All 26 components plus the new multi-level-source component
   (IDEA-032's replacement for the declined `structure.level_distance`
   extension) are implemented, registered, and documented** in
   `ANALYSIS_COMPONENT_CATALOG.md`, each with a passing component-contract
   test.
3. **`statistics.rolling_window_position` (IDEA-030) runs composed on top
   of another component's output**, using the existing
   `ComponentDependency`/`ComponentOutputRef` mechanism confirmed in Wave 0
   — no new registry capability required.
4. **Every component runs error-free and produces its documented output
   shape** when exercised through at least one example Signal Model
   composition or a direct component-contract test — this is the PRD's
   entire correctness bar; no claim is made about predictive or trading
   value of any component's output.
5. **All `session.*` components pass a causal-only check** — no test or
   manual inspection finds a full-period value assigned before that
   period's bar closes.

## Riskiest assumption

**That treating this as one 26-component PRD, split only into Wave A
(parallel, independent) and Wave B (sequenced, dependent), doesn't hide a
dependency that only surfaces during implementation.** The vision doc and
the idea registry already name most cross-pack dependencies explicitly
(IDEA-029's normalizer choice, IDEA-030's composition-capability question,
IDEA-032's sequencing after IDEA-027, IDEA-031's deferred VWAP variant), but
this is the first time all six ideas are being implemented together rather
than read separately — if the architect's Wave 0 pass finds an
undocumented dependency between, say, Wave A components, that is a
stop-and-report finding to bring back to the maintainer, not something to
silently absorb by reordering work.

## Constraints

- **High priority, no fixed calendar deadline** — this PRD goes ahead of
  other currently unapproved tracks (e.g. any further ML signal-promotion
  or dashboard work not yet approved), per explicit maintainer instruction.
- Every ADR and Wave 0 decision set goes back to the maintainer for
  explicit review before implementation starts, matching this project's
  established governance convention.
- No ADR is expected by default, following the precedent that
  `model_authoring` DSL / registry / NumPy-implementation component
  additions have never needed one (Sprint 047, Sprint 048, Sprint 051). If
  Wave 0's composition-capability investigation (IDEA-030) finds the
  registry needs a structural change, that finding earns its own ADR at
  that point — not assumed in advance.

## User story

As the maintainer, I want the full six-idea Market Analysis catalog
expansion built in one coordinated PRD rather than as five scattered
registry entries picked off one at a time, with the simplest, least
dependent components implemented first and in parallel, tooling built early
enough that I'm not paying the manual-registration cost 26 times over, and
the more structurally complex components (shared normalizers, component
composition, extensions of an existing component) following once their
prerequisites exist. I want the catalog implemented and demonstrably
working — no errors, correct output shapes — with judging whether any of it
is actually predictive left for a later, separate piece of work.

## Open questions

- **Shared volatility normalizer for IDEA-029** (`trend.normalized_slope`,
  `momentum.normalized_rate_of_change`) — existing
  `volatility.relative_volatility` vs. new `volatility.range_based_variance`
  (IDEA-028). Left to the architect as a Wave 0 decision, made once, not
  per-component.
- ~~Registry component-composition capability (IDEA-030)~~ — **resolved in
  Wave 0 (2026-09-17)**: the capability already exists
  (`ComponentDependency`/`ComponentOutputRef`); IDEA-030 moved into Wave A.
- ~~`structure.level_distance`'s output-shape generalization (IDEA-032)~~ —
  **resolved in Wave 0 (2026-09-17)**: the existing component's output
  shape does not generalize without breaking existing consumers; maintainer
  chose a new, generic multi-level-source component instead of an in-place
  extension. Remaining open item: its exact name and output shape, per the
  naming convention — architect's design pass.
- **Session-hour definitions (Asia/London/New York) placement** — inside
  IDEA-027's component pack, or as a shared session-calendar reference
  usable by multiple components (also affects IDEA-031's deferred VWAP
  variant). Architect's call.
- **Exact rule set and priority order for `candle.reversal_pattern`
  (IDEA-031)** and **ATR-multiple thresholds for `structure.impulse_origin_range`
  / `structure.range_discontinuity` (IDEA-027)** — calibrated in this
  framework, not copied from the source material's undocumented constants;
  architect proposes, ideally backed by a quick empirical check rather than
  a guess.
- **Promotion criteria common across all six packs vs. pack-specific** (e.g.
  IDEA-027's causal-only gate for `session.*` components doesn't obviously
  generalize to IDEA-028's volatility estimators) — architect states which
  criteria are catalog-wide (naming convention, contract test, catalog
  entry) vs. pack-specific (causal-only gate, threshold calibration) in the
  Wave 0 writeup.

## Handoff

Architect: continue Wave 0 covering (a) the registration-tooling design
(IDEA-010/011) as the first deliverable, (b) the shared IDEA-029 normalizer
decision, (c) the new multi-level-source component's exact name and output
shape for IDEA-032, and (d) session-calendar placement. The
composition-capability question (IDEA-030) and the
extend-vs-new-component question (IDEA-032) are already resolved — see
Goals and the struck-through Open questions above; do not re-litigate them.
Confirm whether Wave A (now including IDEA-027/028/030/031-base components)
and the tooling prerequisite fit one sprint or need splitting from Wave B —
given the explicit simple-first/parallel, complex-later sequencing the
maintainer set, a split between "Wave A + tooling" and "Wave B" sprints is
the likely shape, but don't assume it without checking actual scope size
once tooling and per-component designs are drafted.
