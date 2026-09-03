"""Framework-side fixture strategy exercising ``momentum.rsi`` gated by
``volatility.relative_volatility`` (S051-T009).

Behaviourally identical to the operator-authored example
(``user_data/components/strategies/rsi_relative_volatility_regime.py``,
S051-T009): same Market/Signal condition, same ``BracketExitModel`` /
``EquityPercentRiskModel`` parameters. Only the ``strategy_model_id`` differs
(prefixed ``fixture_``, per the ``uses_candle_wick.py`` / ``uses_bracket_exit.py``
convention, S047-T012 / S048-T012), so a run through this fixture is provably
not falling back to some other strategy.

``user_data/components/strategies/`` is gitignored (ADR-0002), so a committed
test cannot point ``strategy_file`` at the real operator-authored file
directly -- it would not exist in CI or a fresh clone. This fixture is the
committed stand-in, exactly the role ``uses_candle_wick.py`` plays for
Sprint 047's ``candle.wick`` component.

Composition, proving "one catalog, two consumers" for two of Sprint 051's
six new components:

Market Model : ``volatility.relative_volatility_ratio(period=20,
               baseline_period=100) > 1.0`` -- only trade while the current
               20-bar realized volatility exceeds its 100-bar baseline (a
               volatility-regime filter, the "relative" half of the PRD's
               regime bullet).
Signal Model : ``momentum.rsi(period=14) < 30.0``, fired ``ON_TRUE_EDGE`` --
               an oversold RSI crossing gated by the market model's regime
               filter above.
Exit Model   : ``BracketExitModel`` -- 20 bps stop, 20 bps target, 20-bar
               timeout (Sprint 048, reused unchanged).
Risk Model   : ``EquityPercentRiskModel`` -- risk 1% of a $100,000 account
               against a 2-point stop distance (Sprint 048, reused
               unchanged).
"""

from __future__ import annotations

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

FIXTURE_STRATEGY_MODEL_ID = "fixture_rsi_relative_volatility_strategy"

RSI_PERIOD = 14
RSI_OVERSOLD_THRESHOLD = 30.0
RELATIVE_VOLATILITY_PERIOD = 20
RELATIVE_VOLATILITY_BASELINE_PERIOD = 100
RELATIVE_VOLATILITY_RATIO_THRESHOLD = 1.0
STOP_LOSS_BPS = 20.0
TAKE_PROFIT_BPS = 20.0
MAX_BARS = 20
ACCOUNT_EQUITY = Decimal(100_000)
RISK_PERCENT = Decimal("0.01")
STOP_DISTANCE = Decimal("2")


def build_strategy() -> StrategyModelDefinition:
    market = market_model(
        "fixture_rsi_relative_volatility_market",
        when=(
            volatility.relative_volatility_ratio(
                period=RELATIVE_VOLATILITY_PERIOD,
                baseline_period=RELATIVE_VOLATILITY_BASELINE_PERIOD,
            )
            > RELATIVE_VOLATILITY_RATIO_THRESHOLD
        ),
    ).definition

    signal = signal_model(
        "fixture_rsi_relative_volatility_signal",
        direction=LONG,
        when=(momentum.rsi(period=RSI_PERIOD) < RSI_OVERSOLD_THRESHOLD),
        firing=ON_TRUE_EDGE,
    ).definition

    return StrategyModelDefinition(
        strategy_model_id=FIXTURE_STRATEGY_MODEL_ID,
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
