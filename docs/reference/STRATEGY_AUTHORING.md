# Custom Strategy Authoring (`strategy_file`)

This is the operator-facing how-to guide for writing your own Strategy Model
and running it through `trading-cli research run strategy` (Phase 12,
Sprint 047). The design record — why one config key, why no sandbox, the
full loading mechanism — lives in
`docs/adr/ADR-0027-operator-authored-strategy-loading.md`. This document
does not repeat that reasoning; it explains how to author, run and debug a
strategy file as an operator.

---

## 1. The convention

A strategy file is an ordinary `.py` file with exactly one required export:

```python
def build_strategy() -> StrategyModelDefinition:
    ...
```

```text
Name        build_strategy           fixed, conventional, NOT configurable
Signature   zero required arguments  (optional/defaulted parameters are fine)
Returns     StrategyModelDefinition  Market x Signal x Exit x Risk (ADR-0016)
```

Point a config at it with the `strategy_file` key, and run it exactly like
any other `research run strategy` config:

```yaml
research:
  kind: strategy
  strategy:
    dataset_ref: "BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1"
    timeframe: 1m
    strategy_file: user_data/components/strategies/my_strategy.py   # NEW
```

```powershell
uv run trading-cli research run --config <path> --dry-run   # proves it loads
uv run trading-cli research run --config <path>              # runs it
```

`strategy_file` is **optional**. Leave it out and `research run strategy`
behaves exactly as it always has — the Sprint 013 canonical example runs.
This is purely additive; every existing config keeps working unchanged.

There is no function-name field and no `module:function` pair — one path,
one fixed entry point. A dotted import path was deliberately rejected too
(ADR-0027 Alternative 1): it would couple your strategy to `sys.path` layout
this CLI never touches.

---

## 2. The trust model — no sandbox

**Loading a `strategy_file` has the exact same blast radius as running that
file yourself: `uv run python <that file>`.**

> No sandbox. No import restriction. No AST inspection. No subprocess
> isolation. The security model is exactly the model of running any local
> script the operator already trusts. — ADR-0027 §2

That is a deliberate design choice, not an oversight. Sandboxing an
arbitrary operator-supplied Python file is a stated non-goal of the PRD, and
arguably incoherent with the premise that this is *your own code*: an
unrestricted interpreter is one line away regardless of what the loader
restricts. What is not acceptable is leaving this implicit — which is why it
is stated here, in `--help`, and in `docs/reference/OPERATOR_CLI.md`.

Practically:

- a strategy file that reads a file, writes a file, opens a socket, or reads
  an environment variable will do exactly that, the moment it is imported;
- **`--dry-run`'s "touches nothing" guarantee narrows.** The CLI itself
  performs no side effect under `--dry-run` — no dataset registration, no
  simulation, no persisted run. But the loaded module is *your* code and it
  executes at import time (loading happens during plan resolution, so a
  typo'd entry-point name or a wrong return type fails pre-flight instead of
  after a multi-minute dataset read). A strategy file that writes to disk at
  import time will still do so under `--dry-run`. See ADR-0027 §4.
- never put credentials in the strategy file's *config* — the CLI still
  rejects any credential-shaped key in the YAML document itself. What the
  Python file itself does with an environment variable is entirely its own
  business; the CLI neither helps nor blocks it.

---

## 3. Error table

Every failure is pre-flight (loading happens during plan resolution, before
any framework side effect) and every message names
`research.strategy.strategy_file` or the resolved absolute path, so you are
never left staring at a stack trace mid-simulation. The dividing line: if
something is wrong with the file, the convention, or the object it returned,
that's a configuration problem (exit code 2, `ConfigError`). Only an
exception your own `build_strategy()` body raises is a workflow failure
(exit code 1, `WorkflowError`).

| What went wrong | What you'll see | Exit code |
|---|---|---|
| The path doesn't exist, isn't a file, or is a directory | `ConfigError` naming `research.strategy.strategy_file` and the resolved absolute path | 2 |
| The file's extension isn't `.py` | `ConfigError` naming the actual extension | 2 |
| Importing the file raises (a syntax error, a missing import, anything at module scope) | `ConfigError` naming the file, chained from your original exception (`--verbose` shows your traceback) | 2 |
| The file has no `build_strategy` at all | `ConfigError` stating the convention verbatim: a zero-argument `build_strategy()` | 2 |
| `build_strategy` exists but isn't callable (e.g. it's a variable) | `ConfigError` naming the attribute's actual type | 2 |
| `build_strategy` requires one or more arguments | `ConfigError` naming those parameter names | 2 |
| `build_strategy()` itself raises | `WorkflowError`, chained from your original exception | 1 |
| `build_strategy()` returns something that isn't a `StrategyModelDefinition` | `ConfigError` naming the actual returned type | 2 |
| The returned `StrategyModelDefinition` fails the framework's own validation (e.g. an unsupported Exit/Risk model combination) | `ConfigError` carrying the framework's own validation message | 2 |

No exception is ever swallowed: every chained error keeps `__cause__`, so
`--verbose` always shows you your own stack, not just the CLI's summary.

---

## 4. Composing with the catalog

Everything you compose a strategy from is `model_authoring`'s typed DSL —
the same one `user_data/components/strategies/*.py` and the framework's own
canonical examples use. Two components were added this sprint:

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

### Sprint 051 — momentum and regime catalog (Phase 15A)

Six more components, forming a shared momentum/regime catalog: every one of
them is consumable identically by a rule-based Signal Model (below) or
declared as a predictive `FeatureSpec` (PRD success metric 1, "one catalog,
two consumers" — proven by `S051-T009`/`S051-T010`). Zero-denominator /
degenerate-window conventions are stated here exactly once per component;
see each component's own docstring for the full derivation.

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

## 5. Worked examples

Two example strategies live in this sprint's demo, one per new component.
Both are **gitignored** (`user_data/` is not shipped with the repository,
per `docs/adr/ADR-0002-separate-src-and-user-data.md`) — recreate the file
below verbatim before pointing a config at it. Each has a matching, committed
example config under `apps/cli/examples/` you can copy and edit.

### `candle.wick` — a wick-rejection strategy

`user_data/components/strategies/candle_wick_rejection.py`
(config: `apps/cli/examples/research_run_strategy_candle_wick.yaml`):

```python
from decimal import Decimal

from trading_framework.model_authoring import (
    LONG,
    ON_TRUE_EDGE,
    VolatilityState,
    candle,
    market_model,
    signal_model,
    volatility,
)
from trading_framework.strategy import (
    FixedBarsExitModel,
    FixedQuantityRiskModel,
    StrategyModelDefinition,
)


def build_strategy() -> StrategyModelDefinition:
    market = market_model(
        "candle_wick_rejection_market",
        when=(volatility.state(period=14, threshold=5.0) == VolatilityState.HIGH),
    ).definition

    signal = signal_model(
        "candle_wick_rejection_signal",
        direction=LONG,
        when=(candle.lower_wick_ratio() > candle.body_ratio()),
        firing=ON_TRUE_EDGE,
    ).definition

    return StrategyModelDefinition(
        strategy_model_id="candle_wick_rejection",
        market_model=market,
        signal_model=signal,
        exit_model=FixedBarsExitModel(exit_after_bars=10),
        risk_model=FixedQuantityRiskModel(quantity=Decimal(1)),
    )
```

### `structure.level_distance` — a session-low pullback strategy

`user_data/components/strategies/level_distance_pullback.py`
(config: `apps/cli/examples/research_run_strategy_level_distance.yaml`):

```python
from decimal import Decimal

from trading_framework.model_authoring import LONG, market_model, signal_model, structure
from trading_framework.strategy import (
    FixedBarsExitModel,
    FixedQuantityRiskModel,
    StrategyModelDefinition,
)
from trading_framework.time.models.timeframe import Timeframe


def build_strategy() -> StrategyModelDefinition:
    market = market_model(
        "level_distance_pullback_market",
        when=(structure.distance_to_session_low(period=14) < 0.5),
    ).definition

    signal = signal_model(
        "level_distance_pullback_signal",
        direction=LONG,
        when=structure.higher_low_event(pivot_range=15, timeframe=Timeframe("5m")),
    ).definition

    return StrategyModelDefinition(
        strategy_model_id="level_distance_pullback",
        market_model=market,
        signal_model=signal,
        exit_model=FixedBarsExitModel(exit_after_bars=10),
        risk_model=FixedQuantityRiskModel(quantity=Decimal(1)),
    )
```

Both use the existing `FixedBarsExitModel` / `FixedQuantityRiskModel` —
those were the only Exit/Risk models the simulator supported at the time
Sprint 047 wrote these two examples.
`BracketExitModel` / `EquityPercentRiskModel` (stop-loss, take-profit,
equity-relative sizing) were scoped in `docs/adr/ADR-0028-bracket-exit-and-equity-relative-sizing.md`,
declined for Sprint 047, and resumed and shipped in Sprint 048 — see the
next section for worked examples using them.

### Bracket exits and equity-percent sizing (Sprint 048)

Two new models widen what an Exit/Risk pairing can express, on top of the
unchanged `FixedBarsExitModel` / `FixedQuantityRiskModel` pair above. Both are
adopted from `docs/adr/ADR-0028-bracket-exit-and-equity-relative-sizing.md`
unchanged; nothing below is new design, only how to use what shipped.

**`BracketExitModel`** — `stop_loss_bps`, `take_profit_bps`, `max_bars`. On
each bar after entry, the kernel (`research/simulation/kernels/bracket.py`)
checks the bar's high/low against the stop and target prices, and the bar
count against `max_bars`. Three exit reasons are possible in one run:
`stop_loss`, `take_profit`, `max_bars`.

**Two fill conventions in the same trades table.** This is the part worth
reading closely if you're staring at a trades table with mixed exit reasons:

```text
stop_loss / take_profit   fills AT ITS OWN TRIGGER PRICE (the stop or target
                           price itself), with the existing slippage_bps
                           applied against the trade — the same direction
                           _apply_exit_slippage already applies elsewhere.
max_bars                  fills at the NEXT BAR'S OPEN — byte-identical to
                           the FixedBarsExitModel/fixed_bars.py convention.
```

A single `BracketExitModel` strategy can therefore produce exit rows under
**two different fill conventions in the same trades table** — a `stop_loss`
or `take_profit` row priced at its trigger level, and a `max_bars` row priced
at the following bar's open. This is deliberate, not an inconsistency: it is
how you tell, per trade, why that row's fill price was computed the way it
was. `exit_reason` is the column that tells you which convention applied to
that row.

If a bar's low reaches the stop **and** its high reaches the target on the
same bar, **the stop always wins** — no intrabar path reconstruction, no
open-proximity heuristic, no config flag. The entry bar itself is scanned
inclusively (a stop/target can trigger on the same bar the position was
filled on).

**`EquityPercentRiskModel`** — `account_equity`, `risk_percent`,
`stop_distance` (a price-point distance, not bps). The position quantity is
`(account_equity * risk_percent) / stop_distance`, derived **once, at
construction** (`__post_init__`), not recomputed per trade or per bar. It is
**static, authoring-time sizing** — never equity-curve-following,
compounding, or dynamic. If your account grows or shrinks during a run, the
quantity does not change with it; that is TD-026, an accepted gap with its
own repayment trigger in `docs/planning/TECHNICAL_DEBT.md`.

**The operator-owned stop-consistency caveat.** `EquityPercentRiskModel.stop_distance`
is a price-point distance; `BracketExitModel.stop_loss_bps` is a basis-points
distance. **v1 does not cross-validate the two** — the risk model has no
reference price available to convert bps into points, so nothing checks that
your `stop_distance` actually corresponds to your `stop_loss_bps` near the
instrument's price level. If you pair the two models, **you, the operator,
own keeping them consistent.** Get this wrong and the strategy still runs
without error — it just risks a different amount of capital per stop than you
intended. A validation helper that closes this gap, once a reference price is
available to do the bps-to-points conversion, is named as unscheduled
post-sprint direction (`SPRINT_048.md` §12), not a v1 promise.

### Worked examples — Sprint 048 (bracket exits + equity-percent sizing)

Three more example strategies, per `S048_WAVE0_DECISIONS.md` D-S048-11, each
composing at least one of Sprint 048's new catalog components
(`trend.ema_distance`, `volatility.range_expansion`) with one or both of the
new Exit/Risk models. Like the two above, all three are **gitignored**
(`user_data/` — ADR-0002) — recreate the file below verbatim before pointing
a config at it. Each has a matching, committed example config under
`apps/cli/examples/`.

#### `ema_reversion_bracket.py` — `BracketExitModel` in isolation

`user_data/components/strategies/ema_reversion_bracket.py`
(config: `apps/cli/examples/research_run_strategy_ema_reversion_bracket.yaml`):

```python
"""Strategy E1 (Sprint 048) — EMA-distance reversion, on the bracket kernel.

Market Model : ``trend.ema_distance(period=20, atr_period=14) < -0.5`` — price
               is at least half an ATR below its 20-period EMA (a stretched,
               scale-free reversion filter).
Signal Model : the same condition, dense — enter long while the stretch
               holds.
Exit Model   : ``BracketExitModel`` — 10 bps stop, 10 bps target, 15-bar
               timeout.
Risk Model   : fixed 1-lot.

Demonstrates ``BracketExitModel`` in isolation, on the new bracket kernel
(``research/simulation/kernels/bracket.py``). The stop/target/timeout are
tuned so all three exit reasons — ``stop_loss``, ``take_profit`` and
``max_bars`` — are genuinely reachable on the committed OHLCV fixture
(``tests/fixtures/market_data/ohlcv_sample_1m.csv``): a run on that fixture
produces 43 trades split 3 ``stop_loss`` / 3 ``take_profit`` / 37
``max_bars``. A bracket example that only ever times out proves nothing
(D-S048-11) — these parameters are chosen, not guessed, and were verified by
an actual run before being committed here.
"""

from __future__ import annotations

from decimal import Decimal

from trading_framework.model_authoring import LONG, market_model, signal_model, trend
from trading_framework.strategy import (
    BracketExitModel,
    FixedQuantityRiskModel,
    StrategyModelDefinition,
)

STRATEGY_ID = "ema_reversion_bracket"

EMA_PERIOD = 20
ATR_PERIOD = 14
DISTANCE_THRESHOLD_ATR = 0.5
STOP_LOSS_BPS = 10.0
TAKE_PROFIT_BPS = 10.0
MAX_BARS = 15
POSITION_QUANTITY = 1


def build_strategy() -> StrategyModelDefinition:
    stretched_below_ema = (
        trend.ema_distance(period=EMA_PERIOD, atr_period=ATR_PERIOD) < -DISTANCE_THRESHOLD_ATR
    )

    market = market_model(
        "ema_reversion_bracket_market",
        when=stretched_below_ema,
    ).definition

    signal = signal_model(
        "ema_reversion_bracket_signal",
        direction=LONG,
        when=stretched_below_ema,
    ).definition

    return StrategyModelDefinition(
        strategy_model_id=STRATEGY_ID,
        market_model=market,
        signal_model=signal,
        exit_model=BracketExitModel(
            stop_loss_bps=STOP_LOSS_BPS,
            take_profit_bps=TAKE_PROFIT_BPS,
            max_bars=MAX_BARS,
        ),
        risk_model=FixedQuantityRiskModel(quantity=Decimal(POSITION_QUANTITY)),
    )
```

`BracketExitModel` in isolation, on the bracket kernel
(`research/simulation/kernels/bracket.py`) — stop, target and timeout are
all reachable. The stop/target/timeout above are not arbitrary: on the
committed OHLCV fixture (`tests/fixtures/market_data/ohlcv_sample_1m.csv`)
this strategy produces **43 trades, split 3 `stop_loss` / 3 `take_profit` /
37 `max_bars`** — verified by an actual run before being committed, not
asserted without checking. A bracket example that only ever times out
would prove nothing (D-S048-11).

#### `range_expansion_breakout.py` — both new models together

`user_data/components/strategies/range_expansion_breakout.py`
(config: `apps/cli/examples/research_run_strategy_range_expansion_breakout.yaml`):

```python
"""Strategy E2 (Sprint 048) — range-expansion filter + session-high breakout,
on the bracket kernel with equity-percent sizing.

Market Model : ``volatility.range_expansion(period=14) > 1.5`` — the current
               bar's true range is at least 1.5x the 14-period ATR (volatility
               is already expanding, same idea as the volatility-state filter
               in the Sprint 013/047 examples, expressed with the new
               dimensionless component instead).
Signal Model : ``price.close > structure.session_high()`` — same comparison
               as ``session_high_breakout.py`` (Sprint 047).
Exit Model   : ``BracketExitModel`` — 15 bps stop, 30 bps target, 40-bar
               timeout.
Risk Model   : ``EquityPercentRiskModel`` — risk 1% of a $100,000 account
               against a 2-point stop distance (chosen by the operator to
               roughly match the bracket's 15 bps stop near this instrument's
               price level; v1 does not cross-validate the two, D-S048-05).

Demonstrates both new Wave 2 models composed together, end to end through
the CLI (this is the pairing PRD success metric 1 / T012 exercises). Unlike
E1, this example is not required to produce a trade on the committed
one-day fixture to satisfy its purpose here — ``structure.session_high()``
is a running, current-bar-inclusive high (``max(session_high[i-1],
high[i])``), so ``close > session_high()`` can only fire when a bar's close
equals its own high on a fresh session high, which the committed fixture's
single RTH session does not happen to contain. It is exercised end to end
against a longer/live dataset instead; see the STRATEGY_AUTHORING.md note
next to this example for the same caveat as the Sprint 047 precedent
(``session_high_breakout.py``) it borrows the signal from.
"""

from __future__ import annotations

from decimal import Decimal

from trading_framework.model_authoring import (
    LONG,
    ON_TRUE_EDGE,
    market_model,
    price,
    signal_model,
    structure,
    volatility,
)
from trading_framework.strategy import (
    BracketExitModel,
    EquityPercentRiskModel,
    StrategyModelDefinition,
)

STRATEGY_ID = "range_expansion_breakout"

RANGE_EXPANSION_PERIOD = 14
RANGE_EXPANSION_THRESHOLD = 1.5
STOP_LOSS_BPS = 15.0
TAKE_PROFIT_BPS = 30.0
MAX_BARS = 40
ACCOUNT_EQUITY = Decimal(100_000)
RISK_PERCENT = Decimal("0.01")
STOP_DISTANCE = Decimal("2")


def build_strategy() -> StrategyModelDefinition:
    market = market_model(
        "range_expansion_breakout_market",
        when=(
            volatility.range_expansion(period=RANGE_EXPANSION_PERIOD) > RANGE_EXPANSION_THRESHOLD
        ),
    ).definition

    signal = signal_model(
        "range_expansion_breakout_signal",
        direction=LONG,
        when=(price.close > structure.session_high()),
        firing=ON_TRUE_EDGE,
    ).definition

    return StrategyModelDefinition(
        strategy_model_id=STRATEGY_ID,
        market_model=market,
        signal_model=signal,
        exit_model=BracketExitModel(
            stop_loss_bps=STOP_LOSS_BPS,
            take_profit_bps=TAKE_PROFIT_BPS,
            max_bars=MAX_BARS,
        ),
        risk_model=EquityPercentRiskModel(
            account_equity=ACCOUNT_EQUITY,
            risk_percent=RISK_PERCENT,
            stop_distance=STOP_DISTANCE,
        ),
    )
```

Composes `BracketExitModel` and `EquityPercentRiskModel` together, end to
end through the CLI (PRD success metric 1). The `EquityPercentRiskModel`
`stop_distance` (2 points) is the operator's own estimate of what the
bracket's 15 bps stop is worth near this instrument's price level — v1
does not cross-validate the two (D-S048-05), so keeping them consistent is
the operator's responsibility.

**A structural note, not a bug in this example specifically:**
`structure.session_high()` is a running, current-bar-**inclusive** high
(`max(session_high[i-1], high[i])`). Because a bar's own `high` is always
`>= close`, the condition `price.close > structure.session_high()` can only
become true on a bar whose close equals its own (freshly-set) high — a
narrow condition that the committed one-day fixture does not happen to
contain, so this example produces **0 trades** on that fixture specifically.
The strategy still loads and runs end to end through the CLI with no error;
`session_high_breakout.py` (Sprint 047, above) uses the same comparison and
has the same characteristic. Point it at a longer/live dataset to see it
actually fire.

#### `quiet_wick_rejection.py` — the risk-model isolation case

`user_data/components/strategies/quiet_wick_rejection.py`
(config: `apps/cli/examples/research_run_strategy_quiet_wick_rejection.yaml`):

```python
"""Strategy E3 (Sprint 048) — quiet-range wick rejection, on the UNCHANGED
fixed-bars kernel with equity-percent sizing.

Market Model : ``volatility.range_expansion(period=14) < 0.8`` — the current
               bar's true range is below 0.8x the 14-period ATR ("quiet").
Signal Model : ``candle.lower_wick_ratio() > 0.4`` (Sprint 047 component) —
               a long lower wick relative to the bar's own range, read as a
               rejection of lower prices, fired ``ON_TRUE_EDGE``.
Exit Model   : ``FixedBarsExitModel`` — fixed 10-bar hold. Deliberately the
               **unchanged** Sprint 013 exit kernel, not ``BracketExitModel``.
Risk Model   : ``EquityPercentRiskModel`` — risk 1% of a $100,000 account
               against a 2-point stop distance (a sizing reference distance
               only; ``FixedBarsExitModel`` has no stop of its own).

This is the deliberate isolation case (D-S048-11): the new Wave 2 Risk
model, run through the OLD, byte-identical fixed-bars kernel
(``kernels/fixed_bars.py``, not edited this sprint). It proves the
risk-model widening is orthogonal to the bracket exit-model change — a
strategy can adopt equity-percent sizing without touching its exit model at
all. On the committed OHLCV fixture this produces 53 trades, every one
with ``exit_reason == "fixed_bars"`` (the only reason ``FixedBarsExitModel``
ever emits) -- there is intentionally only one distinct reason here, unlike
E1.
"""

from __future__ import annotations

from decimal import Decimal

from trading_framework.model_authoring import LONG, ON_TRUE_EDGE, candle, market_model, signal_model, volatility
from trading_framework.strategy import (
    EquityPercentRiskModel,
    FixedBarsExitModel,
    StrategyModelDefinition,
)

STRATEGY_ID = "quiet_wick_rejection"

RANGE_EXPANSION_PERIOD = 14
QUIET_RANGE_EXPANSION_THRESHOLD = 0.8
LOWER_WICK_RATIO_THRESHOLD = 0.4
EXIT_AFTER_BARS = 10
ACCOUNT_EQUITY = Decimal(100_000)
RISK_PERCENT = Decimal("0.01")
STOP_DISTANCE = Decimal("2")


def build_strategy() -> StrategyModelDefinition:
    market = market_model(
        "quiet_wick_rejection_market",
        when=(
            volatility.range_expansion(period=RANGE_EXPANSION_PERIOD)
            < QUIET_RANGE_EXPANSION_THRESHOLD
        ),
    ).definition

    signal = signal_model(
        "quiet_wick_rejection_signal",
        direction=LONG,
        when=(candle.lower_wick_ratio() > LOWER_WICK_RATIO_THRESHOLD),
        firing=ON_TRUE_EDGE,
    ).definition

    return StrategyModelDefinition(
        strategy_model_id=STRATEGY_ID,
        market_model=market,
        signal_model=signal,
        exit_model=FixedBarsExitModel(exit_after_bars=EXIT_AFTER_BARS),
        risk_model=EquityPercentRiskModel(
            account_equity=ACCOUNT_EQUITY,
            risk_percent=RISK_PERCENT,
            stop_distance=STOP_DISTANCE,
        ),
    )
```

The deliberate isolation case (D-S048-11): `EquityPercentRiskModel` on the
**unchanged** fixed-bars kernel (`kernels/fixed_bars.py`, not touched this
sprint), proving the new sizing model is orthogonal to the new bracket
exit-model change — a strategy can adopt equity-percent sizing without
touching its exit model at all. On the committed OHLCV fixture this
produces 53 trades, every one with `exit_reason == "fixed_bars"` (the only
reason `FixedBarsExitModel` ever emits — intentionally only one distinct
reason here, unlike `ema_reversion_bracket.py` above).

---

### Worked example — Sprint 051 (momentum/regime catalog, both consumption paths)

One example strategy composing two of Sprint 051's six new components
(`momentum.rsi`, `volatility.relative_volatility`), reusing Sprint 048's
`BracketExitModel` / `EquityPercentRiskModel` unchanged, per
`S051_WAVE0_DECISIONS.md` D-S051-08. Like the examples above, it is
**gitignored** (`user_data/` -- ADR-0002); recreate it verbatim before
pointing a config at it. Config:
`apps/cli/examples/research_run_strategy_rsi_relative_volatility.yaml`.

#### `rsi_relative_volatility_regime.py` -- oversold RSI gated by a volatility regime

`user_data/components/strategies/rsi_relative_volatility_regime.py`
(config: `apps/cli/examples/research_run_strategy_rsi_relative_volatility.yaml`):

```python
"""Strategy S051-T009 -- RSI oversold entry, gated by a relative-volatility
regime filter.

Market Model : ``volatility.relative_volatility_ratio(period=20,
               baseline_period=100) > 1.0`` -- only trade while the current
               20-bar realized volatility exceeds its 100-bar baseline (the
               "relative" half of the PRD's regime bullet: only take the
               signal when the volatility regime supports it).
Signal Model : ``momentum.rsi(period=14) < 30.0``, fired ``ON_TRUE_EDGE`` --
               an oversold RSI crossing, gated by the Market Model's regime
               filter above.
Exit Model   : ``BracketExitModel`` -- 20 bps stop, 20 bps target, 20-bar
               timeout (Sprint 048, reused unchanged).
Risk Model   : ``EquityPercentRiskModel`` -- risk 1% of a $100,000 account
               against a 2-point stop distance (Sprint 048, reused
               unchanged; v1 does not cross-validate the bps/points
               distance pairing, D-S048-05 -- same operator-owned caveat as
               the Sprint 048 examples above).
"""

from decimal import Decimal

from trading_framework.model_authoring import (
    LONG,
    ON_TRUE_EDGE,
    market_model,
    momentum,
    signal_model,
    volatility,
)
from trading_framework.strategy import (
    BracketExitModel,
    EquityPercentRiskModel,
    StrategyModelDefinition,
)


def build_strategy() -> StrategyModelDefinition:
    market = market_model(
        "rsi_relative_volatility_regime_market",
        when=(volatility.relative_volatility_ratio(period=20, baseline_period=100) > 1.0),
    ).definition

    signal = signal_model(
        "rsi_relative_volatility_regime_signal",
        direction=LONG,
        when=(momentum.rsi(period=14) < 30.0),
        firing=ON_TRUE_EDGE,
    ).definition

    return StrategyModelDefinition(
        strategy_model_id="rsi_relative_volatility_regime",
        market_model=market,
        signal_model=signal,
        exit_model=BracketExitModel(
            stop_loss_bps=20.0,
            take_profit_bps=20.0,
            max_bars=20,
        ),
        risk_model=EquityPercentRiskModel(
            account_equity=Decimal(100_000),
            risk_percent=Decimal("0.01"),
            stop_distance=Decimal("2"),
        ),
    )
```

The framework-side committed stand-in for this example is
`apps/cli/tests/fixtures/strategies/uses_rsi_relative_volatility.py`
(behaviourally identical, `strategy_model_id` prefixed `fixture_`), which
backs `apps/cli/tests/test_authored_strategy_examples.py`'s end-to-end test
that: the run's `strategy_model_id` is the loaded strategy's, not the
Sprint 013 canonical example's; and both `momentum.rsi` and
`volatility.relative_volatility` genuinely appear in the run's analysis
lineage (`AnalysisResult.computation_identity`), not merely in the loaded
expression tree -- the acceptance criterion PRD success metric 1 requires
(D-S051-08).

## 6. The advisory import convention (not enforced)

Your strategy file can import anything your own Python environment can
import — nothing stops it, and nothing scans it (§7 below). For
portability across environments and framework versions, it *should* only
need:

```text
trading_framework.model_authoring        the DSL (market_model, signal_model, price, ...)
trading_framework.strategy.*             StrategyModelDefinition, Exit/Risk models
trading_framework.time.models.timeframe  Timeframe
```

Reaching deeper — into `research.*`, `infrastructure.*`, or an application
workflow — is legal and will work, but it's a smell: it usually means the
strategy is trying to do something a Market/Signal Model should express
instead. This is **advisory only, never checked at runtime.** Breaking it
costs you portability; it costs the framework nothing, which is exactly why
nothing enforces it.

If your strategy needs a sibling file (a shared helper module, a constants
file), the CLI never mutates `sys.path` on your behalf — that is a
deliberate choice (ADR-0027 §3), not a gap. Set `PYTHONPATH` yourself before
invoking `trading-cli`, or keep your strategy self-contained in one file.

---

## 7. Why the boundary test can't see your strategy file (and never will)

`tests/unit/test_apps_boundaries.py` enforces `apps/cli`'s own 17-module
import allow-list by statically scanning `apps/cli/src`. Your strategy file
is not part of `apps/cli/src` — it typically lives in gitignored
`user_data/`, and CI never sees it. The loader itself needed **zero**
widening of that allow-list to exist: `trading_framework.strategy` was
already on it, and it exports everything the loader needs
(`StrategyModelDefinition`, `StrategyModelDefinitionError`,
`validate_strategy_model_definition`).

A green boundary test is proof about this repository's own source tree. It
is not, and was never intended to be, proof that nothing outside that list
was imported by a loaded strategy at runtime — that gap is logged as
**TD-025** in `docs/planning/TECHNICAL_DEBT.md`, so it is never mistaken for
an oversight.

---

## 8. Related

- `docs/adr/ADR-0027-operator-authored-strategy-loading.md` — the design
  record: loading mechanism, the two import boundaries, error taxonomy.
- `docs/adr/ADR-0028-bracket-exit-and-equity-relative-sizing.md` — the
  Exit/Risk expansion: declined for Sprint 047, resumed and accepted for
  Sprint 048 (`BracketExitModel`, `EquityPercentRiskModel`).
- `docs/reference/OPERATOR_CLI.md` — the full CLI operator guide.
- `apps/cli/CLAUDE.md` — module context for anyone editing `apps/cli`.
- `docs/planning/sprints/SPRINT_048.md`, `S048_WAVE0_DECISIONS.md` — the
  sprint that shipped the three worked examples in §5's second block.
- `docs/planning/sprints/SPRINT_051.md`, `S051_WAVE0_DECISIONS.md` — the
  sprint that shipped the momentum/regime catalog in §4's third block and the
  worked example in §5's third block; §13 Review records the two warm-up
  text corrections referenced above.
- `docs/planning/sprints/SPRINT_047.md`, `S047_WAVE0_DECISIONS.md` — sprint
  scope and binding decisions.
- `docs/planning/TECHNICAL_DEBT.md` TD-025 — the boundary test's blind spot.
