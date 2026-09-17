# Sprint 066: Market Analysis Wave A Component Batch

Status: **Open** — maintainer authorized opening this sprint 2026-09-17.
Goal: Implement Phase 19's Wave A — the 20 remaining simple/independent
Market Analysis components (`structure.opening_gap`, Wave A's pilot, already
shipped in Sprint 065) — using the scaffolding CLI and promotion-readiness
report built in Sprint 065, per the accepted PRD and Wave 0 decision set.

Sources:

- `docs/product/PRD-market-analysis-catalog-expansion-2026-09.md` (APPROVED 2026-09-17)
- `docs/planning/roadmap/PHASE_19_MARKET_ANALYSIS_CATALOG_EXPANSION.md` (APPROVED 2026-09-17)
- `docs/planning/roadmap/PHASE_19_WAVE0_DECISIONS.md` — D-P19-01 (tooling, already built), D-P19-04 (session-calendar placement), D-P19-05 (secondary items: `candle.reversal_pattern` rule set, ATR-multiple defaults, MTF deferral, promotion-criteria split), D-P19-06 (this sprint's scope and 3-sprint plan) — all ACCEPTED (maintainer, 2026-09-17)
- `docs/planning/registries/idea-market-analysis.md#idea-027` (Price-Structure and Session Context — 10 remaining components), `#idea-028` (Volatility Estimators — 5 components), `#idea-030` (Rolling Window Position — 1 component), `#idea-031` (Candle Pattern and Bar-Volume — 4 base components, excludes the deferred session-anchored VWAP variant)
- `docs/planning/sprints/SPRINT_065.md` (Closeout) — the tooling and pilot component this sprint builds on
- `scripts/market_analysis/scaffold_component.py`, `scripts/market_analysis/check_promotion_readiness.py` (Sprint 065, merged to `main`)
- `src/trading_framework/market_analysis/components/structure/opening_gap.py` (closest existing precedent: single ATR dependency, causal, ATR-normalized output)
- `src/trading_framework/time/sessions/cme_es_rth.py` (session-resolver pattern to extend per D-P19-04)
- `docs/reference/modules/ANALYSIS_COMPONENT_CATALOG.md` (catalog entry format)

Architecture triage: **complete and accepted.** D-P19-01 through D-P19-06
were accepted by the maintainer on 2026-09-17
(`PHASE_19_WAVE0_DECISIONS.md`). This sprint does not re-derive scope,
sequencing or the accepted secondary-item decisions (naming convention,
ATR-multiple starting defaults, `candle.reversal_pattern`'s rule set, no
MTF variants, catalog-wide vs. pack-specific promotion criteria). Any
finding that would change one of those is a STOP-AND-REPORT, not an
in-sprint amendment.

## Scope

In scope — 20 components, built in parallel (no cross-component
dependency inside this list; see Riskiest assumption below):

- **Session-calendar module (D-P19-04, prerequisite for the 3 `session.*`
  components below)**: named session-window resolvers (Asia, London, New
  York) added to `src/trading_framework/time/sessions/`, extending the
  existing `TradingSessionResolver` protocol and `CmeEsRthSessionResolver`
  pattern — same UTC-in, IANA-timezone-conversion approach, no new
  timezone-handling code invented.
- **IDEA-027 remaining components (10)**: `structure.range_discontinuity`,
  `structure.impulse_origin_range`, `structure.impulse_follow_through`,
  `structure.level_sweep_rejection`, `structure.level_role_reversal`,
  `structure.matched_extreme_pair`, `structure.close_reversal_level`,
  `session.overlap_window`, `session.previous_period_extreme`,
  `session.current_period_extreme`. All `session.*` components are
  **causal-only from the first implementation** — a hard acceptance gate,
  not a later fix (no full-period high/low assigned before that period's
  bar closes).
- **IDEA-028 (5)**: `volatility.range_based_variance`,
  `volatility.directional_asymmetry`, `volatility.acceleration`,
  `volatility.choppiness_index`, `volatility.regime_state`.
- **IDEA-031 base components (4)**: `candle.reversal_pattern` (the
  accepted 4-pattern rule set: `engulfing` → `level_close_reversal` →
  `rejection_wick` → `none`, per D-P19-05), `candle.smoothed_ohlc`,
  `volume.rolling_weighted_price` (fixed-window variant only —
  session-anchored is deferred to Wave B), `volume.cumulative_trend`.
- **IDEA-030 (1)**: `statistics.rolling_window_position` — a generic
  component consuming another component's `OutputRef` as input, using the
  registry capability Wave 0 already confirmed exists
  (`ComponentDependency`/`ComponentOutputRef`, no new registry work).
- Every component: scaffolded via `scaffold_component.py`, a completed
  `ANALYSIS_COMPONENT_CATALOG.md` entry (formula, warm-up,
  zero-denominator convention, TODO marker removed), a component-contract
  test with real behavioral assertions (not just the scaffolded
  identity/registration stubs), and a clean
  `check_promotion_readiness.py` report (PASS on every applicable check).

Out of scope:

- **Wave B** (IDEA-029, IDEA-032, IDEA-031's deferred VWAP variant) —
  Sprint N+2, depends on this sprint's `structure.matched_extreme_pair`,
  `session.previous_period_extreme`, and the session-calendar module.
- **Signal Research / Strategy Research validation** of any component in
  this batch — out of scope for the whole PRD (see PRD non-goals), not
  just this sprint. "Done" here is implementation-only: a component runs
  error-free and produces its documented output shape.
- **MTF (multi-timeframe) variants** for any of these 20 components —
  D-P19-05 already decided single-timeframe-first applies uniformly, no
  exceptions.
- **Recalibrating** the ATR-multiple starting defaults D-P19-05 already
  set (`structure.impulse_origin_range` `impulse_atr_multiple = 1.5`,
  `structure.range_discontinuity` `min_gap_atr_multiple = 0.1`) against
  real historical data — they ship as documented, calibratable
  parameters; recalibration is a later, separate finding if warranted.
- **IDEA-010/011 tooling changes** — the scaffolding CLI and promotion
  report are used as built in Sprint 065; a real limitation found while
  using them at this scale (e.g. the text-anchor registration patch
  breaking on an edge case) is a STOP-AND-REPORT, not an in-sprint tooling
  fix, unless trivial.

## Decisions

Binding detail and rationale: [`PHASE_19_WAVE0_DECISIONS.md`](../roadmap/PHASE_19_WAVE0_DECISIONS.md),
all six decisions ACCEPTED (maintainer, 2026-09-17). No new Wave 0
decisions are opened in this sprint. Component-level design choices not
already fixed by Wave 0 (e.g. exact output field names beyond what each
idea entry specifies, session-window hour boundaries — D-P19-04
explicitly left exact bounds "TBD by whoever implements this against a
documented reference") are the implementer's call per task, following the
naming convention and the precedent components named in each task below.

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | Session-calendar module: `AsiaSessionResolver`, `LondonSessionResolver`, `NewYorkSessionResolver` (or one parametrized resolver) added to `src/trading_framework/time/sessions/`, following `CmeEsRthSessionResolver`'s UTC-in/IANA-conversion pattern; each returns a `session_id`/membership column set via the existing `TradingSessionResolver` protocol | None | `time/sessions` | high | Done — architecture-triage found the single-resolver-per-run model couldn't support simultaneous multi-session membership; [ADR-MA-015](../../adr/ADR-MA-015-multi-session-trading-calendar-composition.md) (ACCEPTED) designed an additive extension, implemented as `GlobalSessionCalendarResolver` + `TradingSessionMetadata.named_session()`; 32 new tests, full suite green | [#557](https://github.com/folg-code/research-trading-framework/pull/557) |
| T002 | `session.overlap_window`, `session.previous_period_extreme`, `session.current_period_extreme` implemented, registered, causal-only verified, documented, `check_promotion_readiness.py` PASS | T001 | `market_analysis/components/session` (new pack) | high | Done — causal_only_gate PASS on all three; dependencies_declared reports NEEDS-REVIEW (accepted: no-default required params, tool can't guess values); self-review fixed a wrong-exception-type bug in overlap_window; 23 tests, full suite green | [#558](https://github.com/folg-code/research-trading-framework/pull/558) |
| T003 | `structure.range_discontinuity`, `structure.impulse_origin_range`, `structure.impulse_follow_through` implemented (ATR-multiple defaults per D-P19-05), registered, documented, PASS | None | `market_analysis/components/structure` | standard | Done — `impulse_follow_through` is the catalog's first `Causality.RETROSPECTIVE` component; also fixed a real tooling bug (catalog duplicate-check false positive on a mere prose mention); 16 tests, full suite green | [#559](https://github.com/folg-code/research-trading-framework/pull/559) |
| T004 | `structure.level_sweep_rejection`, `structure.level_role_reversal`, `structure.matched_extreme_pair`, `structure.close_reversal_level` implemented, registered, documented, PASS | None | `market_analysis/components/structure` | standard | Done — all four build on `structure.swing` for level bookkeeping (Main Question resolved: reuse over duplication); 14 tests, full suite green | [#560](https://github.com/folg-code/research-trading-framework/pull/560) |
| T005 | `volatility.range_based_variance`, `volatility.directional_asymmetry`, `volatility.acceleration` implemented, registered, documented, PASS | None | `market_analysis/components/volatility` | standard | Done — `range_based_variance` supports Parkinson and Garman-Klass; `directional_asymmetry` computes its own per-bar Parkinson term rather than depending on `range_based_variance` (avoids a dependency for a two-line formula); `acceleration` depends on `volatility.atr`; 12 tests, full suite green | [#561](https://github.com/folg-code/research-trading-framework/pull/561) |
| T006 | `volatility.choppiness_index`, `volatility.regime_state` implemented, registered, documented, PASS | None | `market_analysis/components/volatility` | standard | Done — `choppiness_index` depends on `volatility.true_range`; `regime_state` depends on two `volatility.atr` outputs (fast/slow), structural sibling of `momentum.macd`; 11 tests, full suite green | [#562](https://github.com/folg-code/research-trading-framework/pull/562) |
| T007 | `candle.reversal_pattern` (4-pattern rule set per D-P19-05), `candle.smoothed_ohlc` implemented, registered, documented, PASS | None | `market_analysis/components/candle` | standard | Done — `reversal_pattern` uses `structure.swing` as its level source (not fixed by D-P19-05, chosen for consistency with `structure.level_sweep_rejection`/`level_role_reversal`) and depends on `candle.wick` for rejection-wick geometry; a hand-built fixture confirms the priority order (`level_close_reversal` beats `rejection_wick` when both match); `smoothed_ohlc` is a fully causal Heikin-Ashi transform with no warm-up; 9 tests, full suite green | [#563](https://github.com/folg-code/research-trading-framework/pull/563) |
| T008 | `volume.rolling_weighted_price` (fixed-window), `volume.cumulative_trend` implemented, registered, documented, PASS | None | `market_analysis/components/volume` (new pack) | standard | Done — `rolling_weighted_price` uses `typical_price = (high+low+close)/3` with a zero-volume-window convention (`NaN`, not `0.0`, since outputs are raw price levels not ratios); `cumulative_trend` is the "Price Volume Trend" formula, no dependency, no warm-up; 7 tests, full suite green | [#564](https://github.com/folg-code/research-trading-framework/pull/564) |
| T009 | `statistics.rolling_window_position` implemented (consumes another component's `OutputRef`, e.g. composed on top of a Wave A or existing component's output for its test), registered, documented, PASS | None | `market_analysis/components/statistics` | standard | Done — v1 depends on `volatility.atr` (keyed by `source_period`), same fixed-target-dependency pattern as `momentum.macd`/`trend.ema_distance`/`volatility.regime_state`; `normal` and `empirical` percentile methods are explicit, separate fields (not conflated); a self-review catch: the kernel's own NaN handling didn't cover the source series' own upstream warmup for the `empirical` method's `<=` comparisons, fixed by explicit masking in the component; 6 tests, full suite green | [#565](https://github.com/folg-code/research-trading-framework/pull/565) |

Component-level acceptance detail (exact formula, parameters, output
fields) is not restated here — see each component's own idea-registry
entry (linked in Scope above) and D-P19-05 for the two ATR-multiple
defaults and the `candle.reversal_pattern` rule set. Naming, catalog-entry
and contract-test requirements are catalog-wide per D-P19-05's
promotion-criteria split; the causal-only gate applies only to T002's
three `session.*` components.

## Branch and PR rules

Per the `git-workflow` skill defaults; no project-specific deviation.

```text
main
  └── sprint/market-analysis-wave-a
        ├── feat/session-calendar-module        (T001)
        ├── feat/session-components             (T002, needs T001 merged)
        ├── feat/structure-gap-impulse           (T003)
        ├── feat/structure-level-reversal        (T004)
        ├── feat/volatility-estimators-1         (T005)
        ├── feat/volatility-estimators-2         (T006)
        ├── feat/candle-components               (T007)
        ├── feat/volume-components               (T008)
        └── feat/rolling-window-position         (T009)
```

- Integration branch: `sprint/market-analysis-wave-a`, cut from `main` at
  its then-current head after approval.
- Working branches: `<prefix>/<descriptive-slug>`, cut from the sprint
  branch's current head.
- PR base is always the sprint branch. One final integration PR to `main`
  at sprint close, after review and CI.
- Squash merge for working PRs. `engineer` stops before merge and reports
  the PR URL.
- T003-T009 are mutually independent and may proceed in any order or in
  parallel — no rebase dependency between them. T002 depends on T001
  merging first (it consumes the session resolvers).

## Acceptance criteria

- All 20 components are registered in `default_mvp_registry()`, each with
  a passing component-contract test exercising real behavior (not just
  the scaffolded identity/registration stubs).
- Every component has a completed `ANALYSIS_COMPONENT_CATALOG.md` entry
  with no `<!-- TODO: fill in before promotion -->` marker remaining.
- `check_promotion_readiness.py` reports every applicable check PASS for
  all 20 components; `causal_only_gate` is PASS (not just N/A) for the 3
  `session.*` components specifically.
- No `session.*` component ever assigns a full-period value to a bar
  before that period closes — verified by a dedicated causal-boundary
  test per `session.*` component, following
  `structure.level_distance`'s/`structure.opening_gap`'s existing
  causal-boundary test pattern.
- No MTF variant is added for any of these 20 components.
- The full `market_analysis` test suite stays green throughout (currently
  279 tests before this sprint's additions).
- `ruff check`, `ruff format --check` and `mypy` stay clean on every PR.

## Descope order

If the sprint must shrink, drop in this order — never the reverse:

```text
1. T009  (statistics.rolling_window_position; smallest, most self-contained, easiest to re-route to a follow-up)
2. T008  (volume components; least-connected pack)
3. T006  (volatility.choppiness_index / regime_state; volatility.range_based_variance from T005 has independent value)
4. T004  (structure level/reversal components; T003's gap/impulse components stand alone)
```

T001/T002 are not independently descopable as a pair once started: T001
with no T002 leaves an unused module, but T001 alone is cheap and may ship
ahead of T002 if T002 needs more design time. T003, T005 and T007 are the
sprint's highest-value, most self-contained slices (closest to
`structure.opening_gap`'s precedent) and should be the last dropped if the
sprint must shrink further than the order above.

## Closeout

To be completed when this sprint closes: integrated checks (test counts,
`check_promotion_readiness.py` output for all 20 components), review
notes per PR, documentation reconciliation
(`PHASE_19_MARKET_ANALYSIS_CATALOG_EXPANSION.md`'s sprint table,
`CURRENT_STATUS.md`, `ROADMAP.md`, `planning/README.md`), and remaining
work (opening Sprint N+2 — Wave B).
