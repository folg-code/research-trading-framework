# Strategy Authoring — Worked Examples

> Extracted from the former `docs/reference/modules/STRATEGY_AUTHORING.md`
> §5 ("Worked examples") by Sprint 055 T007, per
> `docs/planning/sprints/SPRINT_055_T004_DECISIONS.md` §1. Content is
> reproduced verbatim — this extraction does not rewrite any example, it
> only moves the cookbook out of the authoring convention document so that
> document is readable at ~250 lines instead of 831. For the `strategy_file`
> convention itself (how to author and run your own strategy file), trust
> model, error table and related links, see
> [`STRATEGY_AUTHORING.md`](STRATEGY_AUTHORING.md).

---

Two example strategies live in this sprint's demo, one per new component.
Both are **gitignored** (`user_data/` is not shipped with the repository,
per `docs/adr/ADR-0002-separate-src-and-user-data.md`) — recreate the file
below verbatim before pointing a config at it. Each has a matching, committed
example config under `apps/cli/examples/` you can copy and edit.

## `candle.wick` — a wick-rejection strategy

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

## `structure.level_distance` — a session-low pullback strategy

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

## Bracket exits and equity-percent sizing (Sprint 048)

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

## Worked examples — Sprint 048 (bracket exits + equity-percent sizing)

Three more example strategies, per `S048_WAVE0_DECISIONS.md` D-S048-11, each
composing at least one of Sprint 048's new catalog components
(`trend.ema_distance`, `volatility.range_expansion`) with one or both of the
new Exit/Risk models. Like the two above, all three are **gitignored**
(`user_data/` — ADR-0002) — recreate the file below verbatim before pointing
a config at it. Each has a matching, committed example config under
`apps/cli/examples/`.

### `ema_reversion_bracket.py` — `BracketExitModel` in isolation

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

### `range_expansion_breakout.py` — both new models together

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

### `quiet_wick_rejection.py` — the risk-model isolation case

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

## Worked example — Sprint 051 (momentum/regime catalog, both consumption paths)

One example strategy composing two of Sprint 051's six new components
(`momentum.rsi`, `volatility.relative_volatility`), reusing Sprint 048's
`BracketExitModel` / `EquityPercentRiskModel` unchanged, per
`S051_WAVE0_DECISIONS.md` D-S051-08. Like the examples above, it is
**gitignored** (`user_data/` -- ADR-0002); recreate it verbatim before
pointing a config at it. Config:
`apps/cli/examples/research_run_strategy_rsi_relative_volatility.yaml`.

### `rsi_relative_volatility_regime.py` -- oversold RSI gated by a volatility regime

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
