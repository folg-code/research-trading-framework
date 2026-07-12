"""Tests for model authoring DSL."""

from trading_framework.market_analysis.registry.builtins import default_mvp_registry
from trading_framework.model_authoring import (
    LONG,
    ON_EVENT,
    VolatilityState,
    market_model,
    price,
    signal_model,
    structure,
    trend,
    volatility,
)
from trading_framework.model_expression.expressions import (
    AndExpression,
    BinaryCompareExpression,
    CompareExpression,
)
from trading_framework.signal_model.definitions import SignalFiringPolicy


def test_market_model_compiles_volatility_state_enum() -> None:
    authored = market_model(
        "high_volatility",
        when=(volatility.state(period=14, threshold=2.0) == VolatilityState.HIGH),
    )

    assert isinstance(authored.expression, CompareExpression)
    assert authored.expression.value == 1.0
    assert authored.definition.market_model_id == "high_volatility"
    assert len(authored.dependencies().component_requests) == 1


def test_market_model_compiles_binary_compare() -> None:
    authored = market_model(
        "bullish_context",
        when=(price.close > trend.ema(period=20)),
    )

    assert isinstance(authored.expression, BinaryCompareExpression)
    assert len(authored.dependencies().component_requests) == 1
    assert authored.dependencies().market_fields[0].value == "close"


def test_market_model_compiles_logical_and() -> None:
    authored = market_model(
        "bullish_high_vol",
        when=(
            (price.close > trend.ema(period=20))
            & (volatility.state(period=14, threshold=2.0) == VolatilityState.HIGH)
        ),
    )

    assert isinstance(authored.expression, AndExpression)


def test_signal_model_event_operand_defaults_to_on_event() -> None:
    authored = signal_model(
        "higher_low_long",
        direction=LONG,
        when=structure.higher_low_event(pivot_range=15, timeframe="5m"),
    )

    assert authored.definition.firing_policy is SignalFiringPolicy.ON_EVENT
    assert isinstance(authored.expression, CompareExpression)
    assert authored.expression.value is True


def test_signal_model_state_condition_defaults_to_on_true_edge() -> None:
    authored = signal_model(
        "high_volatility_edge",
        direction=LONG,
        when=(volatility.state(period=14, threshold=2.0) == VolatilityState.HIGH),
    )

    assert authored.definition.firing_policy is SignalFiringPolicy.ON_TRUE_EDGE


def test_signal_model_combined_infers_on_event() -> None:
    authored = signal_model(
        "high_vol_and_higher_low",
        direction=LONG,
        when=(
            (volatility.state(period=14, threshold=2.0) == VolatilityState.HIGH)
            & structure.higher_low_event(pivot_range=15, timeframe="5m")
        ),
    )

    assert authored.definition.firing_policy is SignalFiringPolicy.ON_EVENT
    assert isinstance(authored.expression, AndExpression)


def test_signal_model_allows_explicit_firing_override() -> None:
    authored = signal_model(
        "high_volatility_edge_explicit",
        direction=LONG,
        when=(volatility.state(period=14, threshold=2.0) == VolatilityState.HIGH),
        firing=ON_EVENT,
    )

    assert authored.definition.firing_policy is ON_EVENT


def test_trend_price_above_ema_helper() -> None:
    authored = market_model("above_ema", when=trend.price_above_ema(period=20))
    assert isinstance(authored.expression, BinaryCompareExpression)


def test_volatility_high_helper() -> None:
    authored = market_model(
        "high_volatility_helper", when=volatility.high(period=14, threshold=2.0)
    )
    assert isinstance(authored.expression, CompareExpression)
    assert authored.expression.value == 1.0


def test_authored_models_validate_against_registry() -> None:
    registry = default_mvp_registry()
    authored = market_model(
        "validated",
        when=(volatility.state(period=14, threshold=2.0) == VolatilityState.HIGH),
        registry=registry,
    )
    assert authored.describe() == "MarketModel('validated')"
