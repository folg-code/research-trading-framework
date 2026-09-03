# PRD — Market Analysis Catalog Expansion for Real-Data Predictive Research

Feature-level PRD within the existing Trading Research Framework product,
following the grill-me discovery pattern established for Phase 2F/11/12/13
and the ML runtime-promotion track (`docs/product/PRD-ml-signal-promotion.md`).
This is the maintainer's stated **second priority** among three ML/AI
directions (after runtime promotion, Sprint 049, now merged to `main`;
before report/dashboard expansion, third).

## Problem

Phase 10 (Predictive Research, Sprints 039–044) validated its whole
methodology — leakage guards, purged/embargoed walk-forward, estimator
families — against **synthetic known-signal CI fixtures only** (ADR-0023 §8,
D-S039-CI-dataset). No real candidate model exists showing genuine
out-of-sample structure on real market data. This is a named, tracked
prerequisite blocking Sprint 050 (Phase 14B, ROADMAP §13F, "Q5": *"a real
(non-synthetic) trained candidate model showing genuine out-of-sample
structure on BTC data — does not exist"*).

Two things changed since that gap was first recorded:

1. **Real data now exists.** Sprint 045 (Phase 2F, ADR-0025, merged #355)
   delivered Binance USD-M historical OHLCV import — `BTCUSDT.P` bars are a
   real, imported `DatasetRef`, not a fixture.
2. **The Market Analysis component catalog feeding features into
   `FeatureSpec` is thin.** It holds ~13 components today
   (`volatility.{true_range,atr,state,range_expansion}`,
   `trend.{ema,slope,ema_distance}`,
   `structure.{swing,session_range,level_distance}`, `candle.wick`) — mostly
   built to prove the DSL and MTF machinery (Sprints 003–006, 037, 048), not
   chosen for their predictive value. Predictive Research studies today can
   only declare features from this narrow set.

Without a bigger catalog, a real-data study is under-featured before it
starts — a negative result would prove nothing about whether structure
exists, only that the framework didn't look hard enough. Without real data,
a bigger catalog proves nothing either. The two are one problem.

## Goals (v1)

- **Expand the Market Analysis component catalog** with momentum/oscillator
  and regime/statistical components, through the existing `model_authoring`
  DSL pattern (precedent: `volatility.atr`, `structure.session_range`,
  `trend.slope`). Priority categories, confirmed by the maintainer:
  - **Momentum/oscillators**: RSI, MACD, stochastic oscillator.
  - **Regime/statistics**: relative/rolling volatility, return
    autocorrelation, return-distribution shape (e.g. rolling skew/kurtosis or
    a simpler regime proxy — architect scopes the exact statistic).
  - These components are **shared infrastructure**: usable by rule-based
    Signal Models exactly like every existing component, AND declarable as
    `FeatureSpec` entries in a `PredictiveStudySpec` — one catalog, two
    consumers, per this framework's existing architecture (no ML-only
    component concept).
- **Run a real Predictive Research study against real Binance BTC futures
  data** (`BTCUSDT.P`, the dataset Sprint 045 imported), using the expanded
  catalog as its feature set, through the existing, unmodified Phase 10
  pipeline (`build_predictive_dataset` → `run_predictive_research` →
  `analyze_predictive_run`).
- **"Done" includes a genuine out-of-sample structure claim, positive or
  negative.** Success is not "a model was trained" — it is a real,
  walk-forward-validated comparison against `RANDOM_PERMUTATION`
  (Phase 10's existing baseline family) on real BTC data. A model that beats
  permutation closes Sprint 050's Q5 prerequisite. A model that does **not**
  beat permutation is also a valid, reportable outcome — it means the
  catalog or the horizon needs more work, not that this PRD failed.
- **CI stays synthetic-only.** This does not touch or reopen ADR-0023 §8
  (D-S039-CI-dataset). The real-data study is a research run the maintainer
  triggers deliberately, not a new CI fixture or a change to what standard
  CI exercises.

## Non-goals (v1)

- **Orderflow or options-derived features.** Stays OHLCV-only, consistent
  with Phase 4B/4C remaining deferred, separate phases.
- **Multi-instrument or cross-asset features.** One instrument (BTC
  futures), matching the existing Predictive Research first-slice limit
  (ADR-0023 §9) and the ML-promotion track's own scope.
- **Reopening CI policy.** ADR-0023 §8 (synthetic-only CI fixtures) is
  unchanged; this PRD's real-data work is a research run, not a CI fixture
  replacement.
- **Restricting to linear/logistic estimator families.** Unlike the
  runtime-promotion track's v1 (which is restricted for a different,
  parity-driven reason — ADR-0029), this track may use any estimator family
  Phase 10 already supports (sklearn baselines, tree families, neural
  families) — the maintainer did not ask for a restriction here.
- **Any change to the promotion mechanism** (Sprint 049's artifact
  format/store/evaluator) or to Sprint 050's planning beyond supplying its
  Q5 prerequisite as an input.

## Success metrics

1. **New components merged and demonstrated in both consumption paths**: at
   least the RSI/MACD/stochastic and relative-volatility/autocorrelation/
   return-distribution components exist in the catalog, each with a passing
   component-contract test, and at least one is exercised by a real example
   Signal Model composition (proving the "shared catalog" claim isn't
   aspirational).
2. **A real Predictive Research run completes end-to-end on `BTCUSDT.P`**
   using the expanded catalog as its declared features — dataset build,
   run, and report, through the unmodified Phase 10 pipeline.
3. **The out-of-sample comparison against `RANDOM_PERMUTATION` is reported
   plainly**, whichever way it goes. If structure is found, this closes
   Sprint 050's Q5. If not, the report states so without hedging, and the
   maintainer decides whether to widen the catalog further or treat the
   negative result as informative and move on.

## Riskiest assumption

**That the new components add real predictive signal on BTC futures, not
just more noise dimensions for a model to overfit.** Named directly by the
maintainer. RSI/MACD/regime-style features are common, well-understood
technical indicators — there is no guarantee they carry structure on this
specific instrument/horizon, and Phase 10's own walk-forward/permutation
discipline exists precisely to catch a model that looks good only because it
was allowed to memorize noise. This PRD treats a rigorous negative result
(the expanded catalog still doesn't beat `RANDOM_PERMUTATION`) as a
legitimate, useful outcome, not a failure to paper over by adding yet more
features until something sticks — that pattern is exactly how spurious
"discoveries" get made, and Phase 10's leakage/purge machinery is what
keeps this PRD honest about it.

## Constraints

- No hard deadline.
- Target instrument: BTC futures (`BTCUSDT.P`), reusing the Binance USD-M
  historical import from Sprint 045 (ADR-0025) — no new data-ingestion work
  implied by this PRD unless the architect finds the imported range
  insufficient for a real walk-forward split (in which case that becomes an
  explicit, separately-scoped finding, not silently absorbed into this
  track).
- Every ADR and Wave 0 decision set goes back to the maintainer for explicit
  review before implementation starts, matching this project's established
  governance convention.

## User story

As the maintainer, I want the Market Analysis catalog to hold enough
genuinely useful technical/statistical building blocks that a Predictive
Research study on real BTC data is a fair test of "is there structure here?"
— not an exercise handicapped by a thin feature set. Once the catalog is
wider, I want to actually run that study on real, imported Binance data and
get a straight answer, walk-forward-validated against a random-permutation
baseline, about whether a real candidate model exists — because that answer
is the missing prerequisite for Sprint 050's promotion-to-runtime work.

## Open questions

- **Exact statistic for the "return-distribution shape" regime component** —
  architect scopes (rolling skew/kurtosis vs. a simpler proxy) against what
  composes well and is causally computable within the existing MTF/warm-up
  machinery.
- **Whether the imported Binance USD-M range is long enough for a
  meaningful purged/embargoed walk-forward** on BTC futures — needs
  verification against the actual imported date range before committing to
  a specific fold count/horizon.
- **Estimator family choice for the real-data run** — sklearn baseline
  first (fastest iteration), or go straight to the tree/neural families
  Phase 10B/10C already support? Left to the architect's sprint design,
  informed by what's cheapest to iterate on before committing to a longer
  run.
- **Whether new components need MTF (multi-timeframe) variants** from day
  one, or whether a single-timeframe first slice is enough — precedent
  (`volatility.atr`, `trend.slope`) suggests components are added
  single-timeframe first and gain MTF projection later; architect confirms
  this pattern still applies.

## Handoff

Architect: design the component catalog additions (exact parameter shapes,
DSL wiring, MTF applicability) and the real-data Predictive Research study
(dataset spec, estimator family choice, fold design against the actual
imported Binance date range) as a Wave 0 decision set, per this project's
established sprint-opening conventions. Confirm whether this fits one sprint
or needs splitting (catalog expansion and the real-data study are more
loosely coupled than Sprint 049's chained tasks were — a split may be more
natural here; don't assume a single sprint by default).
