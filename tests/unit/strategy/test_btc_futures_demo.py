"""Tests for reusable BTC futures demo Strategy Model definitions."""

from decimal import Decimal

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.model_expression.expressions import (
    BinaryCompareExpression,
    CompareExpression,
)
from trading_framework.signal_model import SignalDirection, SignalFiringPolicy
from trading_framework.strategy import (
    BTC_FUTURES_DEMO_DISCLOSURE,
    BTC_FUTURES_DEMO_MARKET_MODEL_ID,
    BTC_FUTURES_DEMO_SIGNAL_MODEL_ID,
    BTC_FUTURES_DEMO_STRATEGY_MODEL_ID,
    BtcFuturesDemoStrategyConfig,
    FixedBarsExitModel,
    FixedQuantityRiskModel,
    build_btc_futures_demo_strategy_model,
    validate_strategy_model_definition,
)


def test_btc_futures_demo_strategy_model_is_research_compatible() -> None:
    definition = build_btc_futures_demo_strategy_model()

    validate_strategy_model_definition(definition)

    assert definition.strategy_model_id == BTC_FUTURES_DEMO_STRATEGY_MODEL_ID
    assert definition.market_model.market_model_id == BTC_FUTURES_DEMO_MARKET_MODEL_ID
    assert definition.signal_model.signal_model_id == BTC_FUTURES_DEMO_SIGNAL_MODEL_ID
    assert definition.signal_model.direction is SignalDirection.LONG
    assert definition.signal_model.firing_policy is SignalFiringPolicy.ON_TRUE_EDGE
    assert isinstance(definition.market_model.expression, CompareExpression)
    assert isinstance(definition.signal_model.expression, BinaryCompareExpression)
    assert isinstance(definition.exit_model, FixedBarsExitModel)
    assert isinstance(definition.risk_model, FixedQuantityRiskModel)
    assert definition.risk_model.position_quantity() == Decimal("0.001")


def test_btc_futures_demo_strategy_config_customizes_model_contracts() -> None:
    config = BtcFuturesDemoStrategyConfig(
        strategy_model_id="btc_demo_fast",
        market_model_id="btc_demo_market",
        signal_model_id="btc_demo_signal",
        ema_period=8,
        exit_after_bars=4,
        quantity=Decimal("0.002"),
    )

    definition = build_btc_futures_demo_strategy_model(config)

    assert definition.strategy_model_id == "btc_demo_fast"
    assert definition.market_model.market_model_id == "btc_demo_market"
    assert definition.signal_model.signal_model_id == "btc_demo_signal"
    assert isinstance(definition.exit_model, FixedBarsExitModel)
    assert definition.exit_model.exit_after_bars == 4
    assert definition.risk_model.position_quantity() == Decimal("0.002")


def test_btc_futures_demo_strategy_config_requires_disclosure() -> None:
    assert "demo" in BTC_FUTURES_DEMO_DISCLOSURE
    assert "unvalidated" in BTC_FUTURES_DEMO_DISCLOSURE

    with pytest.raises(ValidationError, match="demo and unvalidated"):
        BtcFuturesDemoStrategyConfig(disclosure="production strategy")
