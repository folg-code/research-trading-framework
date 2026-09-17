# Analysis Component Catalog

> Merged from the former `docs/reference/modules/STRATEGY_AUTHORING.md` §4
> ("Composing with the catalog" — per-component semantics, warm-up, output
> fields, zero-denominator conventions) and
> [`MARKET_ANALYSIS_MODULE.md`](MARKET_ANALYSIS_MODULE.md)'s "MVP Components"
> table by Sprint 055 T007, per
> `docs/archive/phases/cross-cutting/SPRINT_055_T004_DECISIONS.md` §1. `system/MODULE_MAP.md`
> §6's inline component-catalog table cell now points here instead of
> restating the list. This gives the component catalog one findable home —
> previously a reader asking "what components exist, and what does
> `momentum.stochastic` return on a zero-range window?" had to know the
> answer was filed under a file called `STRATEGY_AUTHORING`.
>
> Per T001's dedup policy, no content is paraphrased — each source's own
> wording is kept, grouped by when the component was added.

---

## MVP components (Sprint 003–005)

From `MARKET_ANALYSIS_MODULE.md`'s original "MVP Components" table, added by
`register_mvp_components`:

| ComponentId | Implementation | Notes |
|-------------|----------------|-------|
| `volatility.true_range` | `numpy.true_range` | OHLC data deps; DSL: `volatility.true_range()` |
| `volatility.atr` | `numpy.atr` | depends on TR output; DSL: `volatility.atr(period=14)` |
| `volatility.state` | `numpy.volatility_state` | ATR + threshold; diagnostic `distance_to_threshold` |
| `trend.ema` | `numpy.ema` | close column; DSL: `trend.ema(period=20)` |
| `trend.slope` | `numpy.ols_slope` | causal OLS of close over `period`; DSL: `trend.slope(period=20)` |
| `structure.swing` | `numpy.swing` | right-window confirmation; DSL: HH/HL/LH/LL events and `latest_*_level` |
| `structure.session_range` | `numpy.session_range` | running ES RTH OHLC/range; DSL: `structure.session_high()` / `session_completed()` |

All components accept optional `computation_timeframe` on `ComponentRequest`.

Swing outputs declare per-field `alignment_policy`: events use `EVENT_AT_AVAILABLE`,
stateful `latest_*` levels use `LAST_CLOSED_BAR` (default).

---

## Sprint 047 additions

From `STRATEGY_AUTHORING.md` §4, "Composing with the catalog": two components
were added this sprint.

- **`candle.wick`** — `candle.upper_wick_ratio()`, `candle.lower_wick_ratio()`,
  `candle.body_ratio()`. Bar-local, causal, no warmup — a rejection candle
  at a level is a common building block.
- **`structure.level_distance`** — `structure.distance_to_session_high(period=14)`,
  `structure.distance_to_session_low(period=14)`. ATR-normalized distance
  from price to the running session high/low. This exists as a *component*,
  not an expression, because the DSL only supports comparisons
  (`==`, `!=`, `>`, `>=`, `<`, `<=`) — there is no arithmetic (`-`, `/`) on an
  `Operand`, so `(price - level) / atr` cannot be written directly in a
  Market/Signal Model condition. `structure.level_distance` does that
  normalization for you.

---

## Sprint 051 — momentum and regime catalog (Phase 15A)

From `STRATEGY_AUTHORING.md` §4: six more components, forming a shared
momentum/regime catalog: every one of them is consumable identically by a
rule-based Signal Model or declared as a predictive `FeatureSpec` (PRD
success metric 1, "one catalog, two consumers" — proven by
`S051-T009`/`S051-T010`). Zero-denominator / degenerate-window conventions
are stated here exactly once per component; see each component's own
docstring for the full derivation.

- **`momentum.rsi`** — `momentum.rsi(period=14)`. Wilder-smoothed RSI of
  close, output `value` in `[0, 100]`. Warm-up: `period` bars. Degenerate
  windows: gains with no losses yields `100.0`; an entirely flat window
  (no gains, no losses) yields the neutral midpoint `50.0`.
- **`momentum.macd`** — `momentum.macd_line`/`macd_signal`/`macd_histogram`
  (`fast_period=12`, `slow_period=26`, `signal_period=9`).
  `line = ema(fast_period) - ema(slow_period)` (depends on two `trend.ema`
  outputs rather than re-deriving EMA); `signal` is the shared `ema` kernel
  applied to `line`; `histogram = line - signal`. `fast_period >= slow_period`
  raises `ComponentValidationError` naming both. Warm-up is derived from its
  two `trend.ema` dependency results plus `signal_period - 1` further bars —
  not a fixed formula independent of `trend.ema`'s own warm-up. No
  zero-denominator case (no division in this component).
- **`momentum.stochastic`** — `momentum.stochastic_k`/`stochastic_d`
  (`period=14`, `smoothing_period=3`). `k` is the rolling `%K` over the
  `period`-bar high/low range; `d` is the SMA of `k` over
  `smoothing_period`. Warm-up: `period + smoothing_period - 2` bars.
  **A zero-range window yields `50.0`, not `0.0`** — a deliberate divergence
  from this catalog's usual zero-denominator convention (D-S051-04): `0.0`
  would fabricate a "close is at the window low" signal for a window that
  isn't actually declining. Every other convention below keeps `0.0`; only
  `momentum.stochastic` diverges, for that stated reason (see the component
  docstring for the full reasoning).
- **`volatility.relative_volatility`** — `volatility.relative_volatility`/
  `relative_volatility_ratio` (`period=20`, `baseline_period=100`, validated
  `period < baseline_period`). `value` is the rolling population standard
  deviation of log returns over `period`; `ratio` is `value / baseline` over
  the wider `baseline_period` window (same estimator). Warm-up:
  `baseline_period` bars. Ordinary zero-denominator convention: a zero
  baseline yields `ratio = 0.0` (D-S048-10).
- **`statistics.return_autocorrelation`** — `statistics.return_autocorrelation(period=60, lag=1)`
  (`period` min 8, `lag` min 1, validated `lag < period - 1`). Rolling
  population Pearson correlation between log returns and their own
  lag-`lag` shift within each `period`-bar window, in `[-1, 1]`. Warm-up:
  `period` bars (NOT `period + lag` — the window already contains exactly
  `period` return values; `lag` only determines how that one fixed-size
  window is split, corrected at Sprint 051's closure, see `SPRINT_051.md`
  §13). Ordinary zero-denominator convention: a zero-variance sub-window
  yields `0.0` (D-S048-10).
- **`statistics.return_distribution`** — `statistics.return_skew`/
  `return_excess_kurtosis(period=60)` (`period` min 8). Rolling population
  Fisher–Pearson skewness and excess kurtosis of log returns (no
  small-sample bias correction — one documented estimator, not a
  library-matching one). Warm-up: `period` bars (NOT `period + 1`, same
  correction as above, see `SPRINT_051.md` §13). Ordinary zero-denominator
  convention: a zero-variance window yields `0.0` for both (D-S048-10).
  **Warning:** short windows on 1-minute bars are outlier-dominated — the
  third/fourth central moments are highly sensitive to a single large
  return inside the window.

All six default `default=True` in `registry/builtins.py` and are reachable
through the same `model_authoring` DSL as every other component in this
catalog.

---

## Sprint 048 additions (referenced by name only)

`trend.ema_distance` and `volatility.range_expansion` are used in the
Sprint 048 worked examples (see
[`STRATEGY_EXAMPLES.md`](STRATEGY_EXAMPLES.md)) but were not separately
documented with warm-up/zero-denominator semantics in the original
`STRATEGY_AUTHORING.md` §4 — carried forward here as a gap rather than
invented, per D-S055-04's no-new-prose discipline.

---

## Phase 19 additions

- **`structure.opening_gap`** — `structure.opening_gap(period=14)` (ATR
  period, min 1). ATR-normalized causal gap between a bar's open and the
  prior bar's close: `gap_atr = (open - prior_close) / atr`. Positive is a
  gap up, negative a gap down. Distinct from `structure.range_discontinuity`
  (a three-bar range gap, not an open-vs-prior-close gap). Depends on
  `volatility.atr` keyed by the same `period`, same pattern as
  `structure.level_distance`. Warm-up: `max(1, period - 1)` bars (the wider
  of this component's own one-bar prior-close lookback and the ATR period —
  in practice the ATR period always dominates for any valid `period >= 2`).
  The first bar has no real prior close; per this framework's `true_range`
  convention it computes as if the prior close equals the bar's own close
  (an `open - close` value, not a true gap), but this is masked by warmup
  regardless. Ordinary zero-denominator convention: a zero ATR (flat market)
  divides through to `inf`/`-inf`/`nan`, not special-cased — the same
  convention `structure.level_distance` already uses.
- **`session.overlap_window`** — `session.overlap_window(session_a, session_b)`,
  both one of `"asia"`, `"london"`, `"new_york"` (required, no default;
  distinct names required). `overlap = 1.0` when the bar is simultaneously
  in both named sessions per `GlobalSessionCalendarResolver`
  (ADR-MA-015), else `0.0`. No warmup — a pure per-bar function of session
  membership, always defined. Requires a resolver carrying the named
  `session_*` columns (`GlobalSessionCalendarResolver`); raises a clear
  error, never silently wrong output, if the configured resolver doesn't
  carry one of the two requested sessions.
- **`session.current_period_extreme`** — `session.current_period_extreme(period, side)`,
  `period` one of `"day"`/`"week"`, `side` one of `"high"`/`"low"`
  (both required, no default). Causal running maximum (`side="high"`) or
  minimum (`side="low"`) of the bar's own `side` column within the current
  `period`, grouped from `session_metadata.trading_days` (day: the
  trading-day itself; week: its ISO `(year, week)`) — any resolver works,
  no named-session column required. No warmup: value is always defined
  from the first bar of the dataset (the running extreme of a
  one-bar-so-far period is that bar's own value).
- **`session.previous_period_extreme`** — `session.previous_period_extreme(period, side)`,
  same parameters as `session.current_period_extreme`, sharing its
  `adapters/numpy/period_extreme.py` kernel. Value is the last *fully
  closed* period's extreme, held constant through the whole following
  period until the next period closes. `NaN` before any period has
  closed (the first period in the dataset has no previous period) — the
  hard causal-only requirement: never includes any bar from the
  still-open current period.
- **`structure.range_discontinuity`** — `structure.range_discontinuity(period=14,
  min_gap_atr_multiple=0.1)` ("fair value gap"). `gap_up_event = 1.0` at
  bar `i` when `low[i] - high[i-2]` exceeds `min_gap_atr_multiple * atr[i]`
  — no overlap between the current bar's range and the range two bars
  back, in the up direction; `gap_down_event` is the mirror
  (`low[i-2] - high[i]`). Distinct from `structure.opening_gap` (an
  open-vs-prior-close gap, not a three-bar range gap). Depends on
  `volatility.atr` keyed by `period`. Warm-up: `max(2, period - 1)` bars.
  `min_gap_atr_multiple` default `0.1` (D-P19-05), a starting,
  calibratable threshold.
- **`structure.impulse_origin_range`** — `structure.impulse_origin_range(period=14,
  impulse_atr_multiple=1.5)` ("order block"). A bar is impulsive when its
  body `|close - open|` spans at least `impulse_atr_multiple * atr`; when
  bar `i` is impulsive and bar `i-1`'s own body is the opposite direction,
  bar `i-1` becomes the active origin range: `origin_event = 1.0` at bar
  `i`, and `origin_high`/`origin_low` (bar `i-1`'s own high/low) plus
  `role_active` (`1.0`) are forward-filled from `i` onward. `role_active`
  flips to `0.0` (invalidated) once a later bar's close breaks back
  through the range — carrying the "breaker" case as a field, not a
  separate component. A new `origin_event` always replaces whatever range
  was previously active. Depends on `volatility.atr` keyed by `period`.
  Warm-up: `max(1, period - 1)` bars. `impulse_atr_multiple` default `1.5`
  (D-P19-05), a starting, calibratable threshold.
- **`structure.impulse_follow_through`** — `structure.impulse_follow_through(period=14,
  impulse_atr_multiple=1.5, lookahead_bars=5)`. The strength-of-continuation
  counterpart to `structure.impulse_origin_range`: for each impulsive bar
  `i` (same impulse definition), `follow_through_atr` is the directional
  extreme move over the next `lookahead_bars` bars, normalized by ATR at
  bar `i` — `(max(high[i+1..i+lookahead_bars]) - close[i]) / atr[i]` for a
  bullish impulse, the mirror for bearish. `NaN` on every non-impulsive
  bar and on an impulsive bar within `lookahead_bars` of the end of the
  dataset (an ordinary within-range `NaN`, not a warmup boundary — this
  component reports no `valid_to_index` truncation; the framework's
  `build_analysis_result` always marks the trailing bar valid, so
  insufficient-lookahead bars are represented as `NaN` values instead, the
  same convention `structure.session_range` already uses for
  outside-RTH bars). **Causality: `RETROSPECTIVE`** — this component's
  value at bar `i` depends on bars strictly after `i`; it is a
  research-only measure, never a live/causal signal. Depends on
  `volatility.atr` keyed by `period`.
- **`structure.matched_extreme_pair`** — `structure.matched_extreme_pair(pivot_range=2,
  period=14, tolerance_atr_multiple=0.1)` ("equal highs/lows"). When
  `structure.swing` confirms a new swing high, `matched_high_event = 1.0`
  if that swing high's price is within `tolerance_atr_multiple * atr` of
  the *previous* confirmed swing high's level. `matched_low_event` is the
  mirror. The first swing of either type has nothing to compare against
  and never matches. Depends on `structure.swing` (keyed by `pivot_range`)
  and `volatility.atr` (keyed by `period`). Warm-up: `max(0, period - 1)`
  bars (the ATR's own warmup; a bar within `structure.swing`'s own warmup
  simply has no swing event to test).
- **`structure.close_reversal_level`** — `structure.close_reversal_level()`
  (no parameters) ("CISD"). At bar `i`, compares the direction of
  `close[i] - close[i-1]` against `close[i-1] - close[i-2]`. When the two
  directions are strictly opposite (both non-zero, opposite sign),
  `reversal_event = 1.0` and `level = close[i-2]` — the close just before
  the prior directional move began. `NaN`/`0.0` elsewhere. Warm-up: 2 bars
  (this component's own lookback only — no dependency).
- **`structure.level_sweep_rejection`** — `structure.level_sweep_rejection(pivot_range=2,
  observation_window=5)` ("liquidity grab"). Using `structure.swing`'s
  latest confirmed swing high/low as the level: when a bar's high pierces
  the *prior* bar's latest swing-high level, and within
  `observation_window` bars (including the pierce bar itself) a bar's
  close falls back below that level, `high_rejection_event = 1.0` fires on
  the rejecting bar. `low_rejection_event` is the mirror. If the window
  elapses with no rejecting close, nothing is flagged — the level was
  genuinely taken out. Depends on `structure.swing` (keyed by
  `pivot_range`) only; no ATR — a plain price comparison, not a normalized
  distance.
- **`structure.level_role_reversal`** — `structure.level_role_reversal(pivot_range=2,
  retest_window=5)` ("SR flip"). Using `structure.swing`'s latest confirmed
  swing high/low as the level: when a bar closes beyond the *prior* bar's
  latest swing-high level (a resistance break), and within `retest_window`
  bars price retests that level from above and holds (a bar's low touches
  back down to it while its close stays at or above it),
  `resistance_to_support_event = 1.0` fires on the confirming bar.
  `support_to_resistance_event` is the mirror. A retest that instead
  breaks back through the level, or a window that elapses with no retest,
  confirms nothing. Depends on `structure.swing` (keyed by `pivot_range`)
  only; no ATR.
- **`volatility.range_based_variance`** — `volatility.range_based_variance(period=20,
  method="parkinson")`. Per bar, computes a range-based variance term —
  Parkinson's `ln(high/low)**2` or Garman-Klass's
  `0.5*ln(high/low)**2 - (2*ln(2)-1)*ln(close/open)**2` — averages it over
  a rolling `period`-bar window, and reports its square root. Uses only the
  current window's own OHLC, no dependency. Warm-up: `period - 1` bars.
  Rejects unknown `method` values at validation time.
- **`volatility.directional_asymmetry`** — `volatility.directional_asymmetry(period=20)`.
  Within a rolling `period`-bar window, splits bars into "up"
  (`close[j] > close[j-1]`) and "down" (`close[j] < close[j-1]`), averages
  each side's Parkinson single-bar variance term separately, and reports
  the square root of each (`up_volatility`, `down_volatility`) plus
  `asymmetry = ln(up_volatility / down_volatility)`. A window with no bars
  of one side yields `NaN` for that side and for `asymmetry`.
  `down_volatility == 0.0` yields `asymmetry = 0.0` (ordinary
  zero-denominator convention). Computes its own per-bar Parkinson term
  directly, no dependency. Warm-up: `period - 1` bars.
- **`volatility.acceleration`** — `volatility.acceleration(period=14)`. The
  first difference of ATR: `value = atr[i] - atr[i-1]` — the rate of change
  of volatility itself, not of price. Depends on `volatility.atr` keyed by
  `period`. Warm-up: `period` bars (ATR's own `period - 1` warmup, plus one
  more bar so both `atr[i]` and `atr[i-1]` are valid).
- **`volatility.choppiness_index`** — `volatility.choppiness_index(period=14)`.
  `100 * log10(sum(true_range, period) / (max(high, period) -
  min(low, period))) / log10(period)`. High (near 100) means the period's
  total true-range path length is close to its net high/low range (choppy,
  range-bound); low (near 0) means the path length greatly exceeds the net
  range (a sustained trend). `period` requires `minimum=2`
  (`log10(1) == 0` would zero the denominator regardless of the price
  data). Depends on `volatility.true_range`; `max(high)`/`min(low)` are
  computed directly. Zero-denominator convention: a perfectly flat window
  forces both the numerator and denominator to `0.0` together, which reads
  as `0.0`, this catalog's ordinary case. Warm-up: `period - 1` bars.
- **`volatility.regime_state`** — `volatility.regime_state(fast_period=5,
  slow_period=20, compression_threshold=0.85, expansion_threshold=1.15)`.
  `ratio = atr(fast_period) / atr(slow_period)`; `state = -1.0`
  ("compression") when `ratio < compression_threshold`, `1.0`
  ("expansion") when `ratio > expansion_threshold`, else `0.0`
  ("balanced"). A second, ratio-based volatility-state vocabulary distinct
  from `volatility.state`'s single-ATR/fixed-threshold LOW/HIGH split.
  Requires `fast_period < slow_period` (rejected otherwise, matching
  `momentum.macd`'s convention). Depends on two `volatility.atr` outputs
  (one per period). Zero-denominator convention: a `0.0` slow ATR (a
  perfectly flat window) yields `ratio = 0.0`, deliberately NOT the
  catalog's usual "0.0 is neutral" reading — a flat slow window is itself
  the most-compressed case, so it falls into `state = -1.0` through the
  same comparison as any other low ratio. Warm-up: the slower ATR's own
  `valid_from_index`.
- **`candle.reversal_pattern`** — `candle.reversal_pattern(pivot_range=2,
  wick_ratio_threshold=2.0)` (D-P19-05). One label per bar/side
  (`bullish_pattern`/`bearish_pattern`), evaluated in fixed priority order,
  first match wins: (1) `engulfing` — the current bar's body fully
  contains the prior bar's body and the two bars close in opposite
  directions; (2) `level_close_reversal` — the bar pierces
  `structure.swing`'s latest confirmed level (as of the *prior* bar) but
  closes back on the origin side, same-bar (not a pending multi-bar event
  like `structure.level_sweep_rejection`); (3) `rejection_wick` — a
  hammer-style single-bar rejection where the rejecting wick is at least
  `wick_ratio_threshold` times the body (via `candle.wick`'s ratios), with
  the opposite wick no larger than the body — a zero-body (doji) bar never
  qualifies; (4) `none` — an explicit, always-assigned label for a
  fully-evaluated bar where nothing matched, distinct from `NaN` ("not yet
  warmed up"). Depends on `structure.swing` (keyed by `pivot_range`) and
  `candle.wick`. Warm-up: 1 bar (`engulfing` needs a prior bar).
- **`candle.smoothed_ohlc`** — `candle.smoothed_ohlc()` (no parameters).
  Causal smoothed-OHLC ("Heikin-Ashi") transform: `close = (open + high +
  low + close) / 4`; `open` recurses from the prior bar's own smoothed
  open/close (seeded at bar 0 as `(open[0] + close[0]) / 2`); `high`/`low`
  are the raw bar's own high/low widened (never narrowed) to also contain
  the smoothed open/close. No dependency, no external period parameter, so
  no warm-up — every bar is valid from bar 0.
- **`volume.rolling_weighted_price`** — `volume.rolling_weighted_price(period=20,
  band_multiplier=2.0)`. A fixed ``period``-bar rolling window only —
  explicitly NOT a session-anchored VWAP (deferred to Wave B).
  `typical_price = (high + low + close) / 3`; `value` is the
  volume-weighted average of `typical_price` over the window;
  `deviation` is the volume-weighted standard deviation of `typical_price`
  around that same `value`; `upper_band`/`lower_band` are `value +/-
  band_multiplier * deviation`. Zero-volume-window convention: a window
  with no volume at all leaves every output `NaN` — a deliberate
  divergence from this catalog's usual "0.0 on zero-denominator"
  convention, since these outputs are raw price levels, not ratios. No
  dependency. Warm-up: `period - 1` bars.
- **`volume.cumulative_trend`** — `volume.cumulative_trend()` (no
  parameters; formerly "Price Volume Trend"). `value[0] = 0.0`; `value[i]
  = value[i-1] + volume[i] * (close[i] - close[i-1]) / close[i-1]` —
  volume added on up bars, subtracted on down bars, scaled by the bar's
  own percent price change (not a flat sign, unlike its simpler cousin
  On-Balance Volume). Zero-denominator convention: `close[i-1] == 0.0`
  defines that bar's percent change as `0.0` (this catalog's ordinary
  convention). No dependency, no external period parameter, so no
  warm-up.
- **`statistics.rolling_window_position`** — `statistics.rolling_window_position(source_period=14,
  window=20, method="normal")` (IDEA-030). A generic building block:
  position of another component's output within its own trailing
  ``window``-bar window. This v1 depends on `volatility.atr` (keyed by
  `source_period`), the same fixed-target-dependency pattern already used
  by `momentum.macd`/`trend.ema_distance`/`volatility.regime_state`, to
  demonstrate the composition. `z_score = (source - mean(source, window))
  / stdev(source, window)` (population stdev). `percentile` is kept
  separate from `z_score` per `method`: `"normal"` (default) is the
  standard-normal CDF of `z_score`; `"empirical"` is the fraction of the
  window's values `<= source`, no distributional assumption. Zero-variance
  convention: a perfectly flat window defines `z_score = 0.0` (this
  catalog's ordinary zero-denominator convention), from which the
  `"normal"` percentile falls out as `0.5`. Warm-up: the source ATR's own
  `valid_from_index` plus `window - 1` further bars.
- **`trend.normalized_slope`** — `trend.normalized_slope(slope_period=20,
  volatility_period=20, baseline_period=100)` (IDEA-029). `value =
  trend.slope(slope_period) / volatility.relative_volatility(
  volatility_period, baseline_period).value` — the shared normalizer
  decided once for the whole IDEA-029 pack (D-P19-02), comparable across
  volatility regimes unlike `trend.slope`'s raw price-per-bar units.
  Depends on `trend.slope` and `volatility.relative_volatility`.
  Zero-denominator convention: this catalog's ordinary convention — a
  flat volatility window (`value == 0.0`) defines `value = 0.0` (a flat
  close window also makes the slope itself `0.0`). Warm-up: the later of
  the two dependencies' own `valid_from_index`.
- **`momentum.normalized_rate_of_change`** — `momentum.normalized_rate_of_change(
  lookback=10, volatility_period=20, baseline_period=100)` (IDEA-029).
  `raw = ln(close[i] / close[i - lookback])`, computed directly (no
  `momentum.rate_of_change` component exists to depend on); `value = raw
  / volatility.relative_volatility(volatility_period,
  baseline_period).value`, the same shared normalizer as
  `trend.normalized_slope`. Depends on `volatility.relative_volatility`
  only. Zero-denominator convention: this catalog's ordinary convention —
  a flat volatility window defines `value = 0.0`. Warm-up: the later of
  `lookback` bars and the volatility dependency's own `valid_from_index`.
