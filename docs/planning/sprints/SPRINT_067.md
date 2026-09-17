# Sprint 067: Market Analysis Wave B Component Batch

Status: **Open** — maintainer authorized opening this sprint 2026-09-17.
Goal: Implement Phase 19's Wave B — the 6 components identified in Wave 0
as depending on Wave A's outputs: two volatility-normalized trend/momentum
components (IDEA-029), a generic multi-level-source distance component
plus two Fibonacci-level components (IDEA-032), and IDEA-031's deferred
session-anchored VWAP variant — using the scaffolding CLI and
promotion-readiness report built in Sprint 065, per the accepted PRD and
Wave 0 decision set.

Sources:

- `docs/product/PRD-market-analysis-catalog-expansion-2026-09.md` (APPROVED 2026-09-17)
- `docs/planning/roadmap/PHASE_19_MARKET_ANALYSIS_CATALOG_EXPANSION.md` (APPROVED 2026-09-17)
- `docs/planning/roadmap/PHASE_19_WAVE0_DECISIONS.md` — D-P19-02 (shared volatility normalizer: `volatility.relative_volatility.value`), D-P19-03 (`structure.distance_to_level`'s name and fixed-named-field output shape), D-P19-04 (session-calendar module, already built in Sprint 066 T001) — all ACCEPTED (maintainer, 2026-09-17)
- `docs/planning/registries/idea-market-analysis.md#idea-029` (Trend and Momentum Efficiency — 2 of its 3 proposed components are in this sprint's scope; see Out of scope), `#idea-031` (deferred session-anchored VWAP variant only — the 4 base components shipped in Sprint 066 T007/T008), `#idea-032` (Level Distance Extension and Fibonacci Levels — 3 components)
- `docs/planning/sprints/SPRINT_066.md` (Closeout) — Wave A, this sprint's prerequisite: `structure.matched_extreme_pair`, `session.previous_period_extreme`, `GlobalSessionCalendarResolver`/`TradingSessionMetadata.named_session()`
- `scripts/market_analysis/scaffold_component.py`, `scripts/market_analysis/check_promotion_readiness.py` (Sprint 065, merged to `main`)
- `src/trading_framework/market_analysis/components/structure/level_distance.py` (precedent for the ATR-normalized-distance pattern `structure.distance_to_level` generalizes)
- `src/trading_framework/market_analysis/components/momentum/macd.py`, `volatility/regime_state.py` (precedent for a component depending on two same-shape outputs keyed by different parameters)
- `docs/reference/modules/ANALYSIS_COMPONENT_CATALOG.md` (catalog entry format)

Architecture triage: **mostly complete.** D-P19-02 through D-P19-04 were
accepted by the maintainer on 2026-09-17
(`PHASE_19_WAVE0_DECISIONS.md`) and cover the shared normalizer,
`structure.distance_to_level`'s name/shape, and the session-calendar
placement. Two design points were left explicitly open at Wave 0 time and
are this sprint's implementer's call (not new Wave 0 decisions, since
neither changes scope, sequencing, or a previously-accepted choice):

- The exact `ComponentOutputRef` mapping for `structure.distance_to_level`'s
  `"previous_day_high"`/`"previous_day_low"`/`"matched_extreme_pair_high"`/`"matched_extreme_pair_low"`
  level sources (D-P19-03 names the pattern and gives the
  `previous_day_high` example; the remaining mappings follow the same
  pattern once `session.previous_period_extreme`'s and
  `structure.matched_extreme_pair`'s actual output IDs are read).
- The deferred VWAP variant's exact component ID and parameter shape
  (IDEA-031 left this "TBD by whoever implements this against a
  documented reference," same framing D-P19-04 used for session-hour
  bounds).

Any finding that would change scope, sequencing, or one of D-P19-02/03/04's
accepted choices is a STOP-AND-REPORT, not an in-sprint amendment.

## Scope

In scope — 6 components:

- **IDEA-029 (2 of 3 proposed components)**: `trend.normalized_slope`
  (`trend.slope` divided by `volatility.relative_volatility.value`, per
  D-P19-02) and `momentum.normalized_rate_of_change`
  (`ln(close_t / close_{t-N})`, computed directly — no
  `momentum.rate_of_change` component exists yet to depend on — divided
  by `volatility.relative_volatility.value`). Both standalone components
  with a real division inside `compute()`, not a DSL composition pattern
  (D-P19-02's Follow-on note; the DSL cannot express arithmetic on an
  `Operand`).
- **IDEA-032 (3 components)**: `structure.distance_to_level` (D-P19-03:
  one row per bar, fixed named `distance_to_<source>_atr` fields per a
  `level_sources` list parameter, wiring `structure.session_range`,
  `session.previous_period_extreme`, and `structure.matched_extreme_pair`
  as configurable sources plus `volatility.atr`),
  `structure.fibonacci_retracement_level`, and
  `structure.fibonacci_extension_level` (both computed from
  `structure.swing`'s latest confirmed swing high/low at documented
  ratios).
- **IDEA-031 (1 component)**: the deferred session-anchored VWAP variant
  of `volume.rolling_weighted_price` — resets its volume-weighted average
  at each session boundary using `TradingSessionMetadata` from Sprint 066
  T001, instead of a fixed rolling bar count.
- Every component: scaffolded via `scaffold_component.py`, a completed
  `ANALYSIS_COMPONENT_CATALOG.md` entry (formula, warm-up,
  zero-denominator convention, TODO marker removed), a component-contract
  test with real behavioral assertions, and a clean
  `check_promotion_readiness.py` report (PASS on every applicable check).

Out of scope:

- **`trend.movement_efficiency`** (IDEA-029's third proposed component,
  `abs(close_t - close_{t-N}) / sum(true_range over N)`) — the
  Phase 19 roadmap doc's Wave B line item explicitly enumerates 6
  components (`trend.normalized_slope`, `momentum.normalized_rate_of_change`,
  the 3 IDEA-032 components, and IDEA-031's VWAP variant) and does not
  include it. It needs no shared-normalizer decision (it's a
  self-contained ratio, unlike the other two IDEA-029 components) and can
  ship independently whenever prioritized; treated here as a deliberate,
  pre-existing scope boundary from the Phase 19 roadmap doc, not a
  descope decision made in this sprint.
- **Signal Research / Strategy Research validation** of any component in
  this batch — out of scope for the whole PRD (see PRD non-goals), not
  just this sprint. "Done" here is implementation-only.
- **MTF (multi-timeframe) variants** for any of these 6 components —
  D-P19-05 (Sprint 066) already decided single-timeframe-first applies
  uniformly across the whole PRD, no exceptions.
- **Extending `structure.level_distance` in place** — D-P19-03 already
  decided against this; `structure.level_distance` stays exactly as-is,
  `structure.distance_to_level` is the new, separate generalization.
- **IDEA-010/011 tooling changes** — used as built; a real limitation
  found while using them is a STOP-AND-REPORT, not an in-sprint tooling
  fix, unless trivial.

## Decisions

Binding detail and rationale: [`PHASE_19_WAVE0_DECISIONS.md`](../roadmap/PHASE_19_WAVE0_DECISIONS.md)
D-P19-02/03/04, all ACCEPTED (maintainer, 2026-09-17). No new Wave 0
decisions are opened in this sprint. The two open design points named in
Architecture triage above (the exact `level_sources` dependency mapping,
and the VWAP variant's component ID/parameter shape) are the
implementer's call per task, following the naming convention and the
precedent components named in each task below.

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | `trend.normalized_slope`, `momentum.normalized_rate_of_change` implemented, registered, documented, `check_promotion_readiness.py` PASS | None (Wave A complete) | `market_analysis/components/trend`, `components/momentum` | standard | Done — both depend on `volatility.relative_volatility.value` per D-P19-02; `normalized_rate_of_change` computes its own `ln(close_t/close_{t-N})` directly (no `momentum.rate_of_change` component exists yet to depend on); both use this catalog's ordinary zero-denominator convention (`value = 0.0` on a flat volatility window); 8 tests, full suite green | [#567](https://github.com/folg-code/research-trading-framework/pull/567) |
| T002 | `structure.distance_to_level` implemented (all six level sources wired: `session_high`, `session_low`, `previous_day_high`, `previous_day_low`, `matched_extreme_pair_high`, `matched_extreme_pair_low`), registered, documented, PASS | None | `market_analysis/components/structure` | high | Done — architecture triage found the registry cannot vary a component's `OutputSchema` per `ComponentRequest` (one singleton instance per `component_id`), so D-P19-03's caller-configurable `level_sources` subset isn't implementable as specified; per maintainer decision, all six `distance_to_<source>_atr` fields are always declared and computed instead (no `level_sources` parameter). Also an additive change to `structure.matched_extreme_pair` (`ComponentVersion` 1.1.0): adds `latest_matched_*_level` outputs — it previously had no continuous level to depend on, only boolean event flags. Self-review caught a real bug: zero-ATR was overriding a `NaN` level (no previous day/match yet) into a fabricated `0.0`. 8 tests, full suite green | [#568](https://github.com/folg-code/research-trading-framework/pull/568) |
| T003 | `structure.fibonacci_retracement_level`, `structure.fibonacci_extension_level` implemented (ratios confirmed against `structure.swing`'s latest confirmed swing high/low), registered, documented, PASS | None | `market_analysis/components/structure` | standard | Done — the "active leg" is chosen by comparing `structure.swing`'s `latest_swing_*_observed_index` (an up-leg or down-leg); retracement and extension share the same two linear formulas, swapped by direction; no zero-denominator case (linear interpolation, not division); hand-computed values cross-checked via a debug run against the exact swing structure the test fixture produces; 6 tests, full suite green | [#569](https://github.com/folg-code/research-trading-framework/pull/569) |
| T004 | Session-anchored VWAP variant of `volume.rolling_weighted_price` implemented (component ID and parameter shape decided as part of this task), registered, documented, PASS | None (session-calendar module already in `main`) | `market_analysis/components/volume` | high | Done — named `volume.session_weighted_price`; reuses `structure.session_range`'s exact session-boundary convention (new session at a trading day's first RTH bar, or the first RTH bar after a non-RTH gap) rather than inventing a new one; no component dependency, reads OHLCV and session metadata directly; dedicated tests confirm no carryover across a new day or a non-RTH gap; 7 tests, full suite green | [#570](https://github.com/folg-code/research-trading-framework/pull/570) |

Component-level acceptance detail (exact formula, parameters, output
fields) is not restated here — see each component's own idea-registry
entry (linked in Scope above) and D-P19-02/03 for the normalizer choice
and `structure.distance_to_level`'s output shape. Naming, catalog-entry
and contract-test requirements are catalog-wide per D-P19-05's
promotion-criteria split (Sprint 066).

## Branch and PR rules

Per the `git-workflow` skill defaults; no project-specific deviation.

```text
main
  └── sprint/market-analysis-wave-b
        ├── feat/normalized-trend-momentum       (T001)
        ├── feat/distance-to-level               (T002)
        ├── feat/fibonacci-levels                (T003)
        └── feat/session-anchored-vwap           (T004)
```

- Integration branch: `sprint/market-analysis-wave-b`, cut from `main` at
  its then-current head after approval.
- Working branches: `<prefix>/<descriptive-slug>`, cut from the sprint
  branch's current head.
- PR base is always the sprint branch. One final integration PR to `main`
  at sprint close, after review and CI.
- Squash merge for working PRs. `engineer` stops before merge and reports
  the PR URL.
- All four tasks are mutually independent and may proceed in any order
  or in parallel — no rebase dependency between them.

## Acceptance criteria

- All 6 components are registered in `default_mvp_registry()`, each with
  a passing component-contract test exercising real behavior (not just
  the scaffolded identity/registration stubs).
- Every component has a completed `ANALYSIS_COMPONENT_CATALOG.md` entry
  with no `<!-- TODO: fill in before promotion -->` marker remaining.
- `check_promotion_readiness.py` reports every applicable check PASS for
  all 6 components.
- `structure.distance_to_level` always declares and computes all six
  level sources named in T002 (no configurable subset — see T002's own
  note on why `level_sources` as a caller-configurable parameter is not
  implementable in this registry).
- The VWAP variant never resets mid-session or carries a prior session's
  accumulated volume/price sum across a session boundary — verified by a
  dedicated causal/session-boundary test, following T002's (Sprint 066)
  `session.*` causal-boundary test pattern.
- No MTF variant is added for any of these 6 components.
- The full `market_analysis` test suite stays green throughout (currently
  372 tests before this sprint's additions).
- `ruff check`, `ruff format --check` and `mypy` stay clean on every PR.

## Descope order

If the sprint must shrink, drop in this order — never the reverse:

```text
1. T004  (VWAP variant; the least self-contained task, still needs a naming/design decision)
2. T003  (Fibonacci levels; independently useful but not blocking the other tasks)
```

T001 and T002 are this sprint's highest-value, most self-contained slices
(T001 mirrors `structure.level_distance`'s existing division-inside-`compute()`
pattern exactly; T002 is IDEA-032's core ask) and should be the last
dropped if the sprint must shrink further than the order above.

## Closeout

To be completed when this sprint closes: integrated checks (test counts,
`check_promotion_readiness.py` output for all 6 components), review
notes per PR, documentation reconciliation
(`PHASE_19_MARKET_ANALYSIS_CATALOG_EXPANSION.md`'s sprint table,
`CURRENT_STATUS.md`, `ROADMAP.md`, `planning/README.md`), and a decision
on `trend.movement_efficiency`'s disposition (a follow-up sprint, or
folded into a future batch).
