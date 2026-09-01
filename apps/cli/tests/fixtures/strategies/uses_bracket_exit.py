"""Framework-side fixture strategy exercising ``BracketExitModel`` (S048-T012).

Behaviourally identical to the operator-authored example E1
(``user_data/components/strategies/ema_reversion_bracket.py``, S048-T011):
same Market/Signal condition, same ``BracketExitModel`` parameters, same
``FixedQuantityRiskModel`` quantity. Only the ``strategy_model_id`` differs
(prefixed ``fixture_`` per the ``uses_candle_wick.py`` convention, S047-T012),
so a run through this fixture is provably not falling back to some other
strategy.

``user_data/components/strategies/`` is gitignored (ADR-0002), so a committed
test cannot point ``strategy_file`` at the real E1 file directly -- it would
not exist in CI or a fresh clone. This fixture is the committed stand-in,
exactly the role ``uses_candle_wick.py`` plays for Sprint 047's
``candle.wick`` component.

E1's stop/target/timeout parameters are deliberately tuned (and were verified
by an actual run before being committed to the real E1 file) so all three
``BracketExitModel`` exit reasons -- ``stop_loss``, ``take_profit`` and
``max_bars`` -- are genuinely reachable on the committed OHLCV fixture
(``tests/fixtures/market_data/ohlcv_sample_1m.csv``): a run on that fixture
produces 43 trades split 3 ``stop_loss`` / 3 ``take_profit`` / 37
``max_bars``. This fixture reuses those exact parameters so the same split
is reproducible here, proving PRD success metric 1 for Sprint 048: more than
one distinct ``exit_reason`` in one run's trades table.
"""

from __future__ import annotations

from decimal import Decimal

from trading_framework.model_authoring import LONG, market_model, signal_model, trend
from trading_framework.strategy import (
    BracketExitModel,
    FixedQuantityRiskModel,
    StrategyModelDefinition,
)

FIXTURE_STRATEGY_MODEL_ID = "fixture_bracket_exit_strategy"

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
        "fixture_bracket_exit_market",
        when=stretched_below_ema,
    ).definition

    signal = signal_model(
        "fixture_bracket_exit_signal",
        direction=LONG,
        when=stretched_below_ema,
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
        risk_model=FixedQuantityRiskModel(quantity=Decimal(POSITION_QUANTITY)),
    )
