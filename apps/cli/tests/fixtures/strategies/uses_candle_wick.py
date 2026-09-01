"""Framework-side fixture strategy exercising ``candle.wick`` (S047-T012).

Unlike the operator-authored examples under the gitignored
``user_data/components/strategies/``, this fixture is committed -- it backs
the end-to-end test asserting the PRD's two success metrics against a real
CLI run: the run manifest's ``strategy_model_id`` is this fixture's, not the
Sprint 013 canonical example's (metric 1), and the loaded Market Model
actually composes the new ``candle.wick`` component (metric 2, component
half -- Wave 2's Exit/Risk half is deferred).
"""

from __future__ import annotations

from decimal import Decimal

from trading_framework.model_authoring import LONG, candle, market_model, signal_model, structure
from trading_framework.strategy import (
    FixedBarsExitModel,
    FixedQuantityRiskModel,
    StrategyModelDefinition,
)
from trading_framework.time.models.timeframe import Timeframe

FIXTURE_STRATEGY_MODEL_ID = "fixture_candle_wick_strategy"


def build_strategy() -> StrategyModelDefinition:
    market = market_model(
        "fixture_candle_wick_market",
        when=(candle.upper_wick_ratio() > candle.body_ratio()),
    ).definition

    signal = signal_model(
        "fixture_candle_wick_signal",
        direction=LONG,
        when=structure.higher_low_event(pivot_range=15, timeframe=Timeframe("5m")),
    ).definition

    return StrategyModelDefinition(
        strategy_model_id=FIXTURE_STRATEGY_MODEL_ID,
        market_model=market,
        signal_model=signal,
        exit_model=FixedBarsExitModel(exit_after_bars=5),
        risk_model=FixedQuantityRiskModel(quantity=Decimal(1)),
    )
