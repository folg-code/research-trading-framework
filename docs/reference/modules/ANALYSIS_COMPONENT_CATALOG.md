# Analysis Component Catalog

> Merged from the former `docs/reference/modules/STRATEGY_AUTHORING.md` §4
> ("Composing with the catalog" — per-component semantics, warm-up, output
> fields, zero-denominator conventions) and
> [`MARKET_ANALYSIS_MODULE.md`](MARKET_ANALYSIS_MODULE.md)'s "MVP Components"
> table by Sprint 055 T007, per
> `docs/planning/sprints/SPRINT_055_T004_DECISIONS.md` §1. `system/MODULE_MAP.md`
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
