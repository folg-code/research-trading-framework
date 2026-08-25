"""Tests for model authoring DSL."""

from trading_framework.market_analysis import ComponentId, OutputId
from trading_framework.market_analysis.components.volatility import (
    AtrComponent,
    TrueRangeComponent,
)
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
    ComparisonOperator,
)
from trading_framework.model_expression.references import (
    ComponentOutputReference,
    MarketField,
    MarketFieldReference,
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


def test_market_model_compiles_atr() -> None:
    authored = market_model(
        "close_above_atr",
        when=(price.close > volatility.atr(period=14)),
        registry=default_mvp_registry(),
    )

    assert isinstance(authored.expression, BinaryCompareExpression)
    assert authored.expression.operator is ComparisonOperator.GT
    assert authored.expression.left == MarketFieldReference(field=MarketField.CLOSE)
    assert isinstance(authored.expression.right, ComponentOutputReference)
    assert authored.expression.right.component_id == ComponentId("volatility.atr")
    assert authored.expression.right.output_id == OutputId("value")
    assert authored.expression.right.parameters == AtrComponent().parameter_schema.canonicalize(
        {"period": 14}
    )
    requests = authored.dependencies().component_requests
    assert len(requests) == 1
    assert requests[0].component_id == ComponentId("volatility.atr")
    assert authored.dependencies().market_fields[0].value == "close"


def test_market_model_compiles_true_range() -> None:
    authored = market_model(
        "close_above_true_range",
        when=(price.close > volatility.true_range()),
        registry=default_mvp_registry(),
    )

    assert isinstance(authored.expression, BinaryCompareExpression)
    assert authored.expression.operator is ComparisonOperator.GT
    assert authored.expression.left == MarketFieldReference(field=MarketField.CLOSE)
    assert isinstance(authored.expression.right, ComponentOutputReference)
    assert authored.expression.right.component_id == ComponentId("volatility.true_range")
    assert authored.expression.right.output_id == OutputId("value")
    assert (
        authored.expression.right.parameters
        == TrueRangeComponent().parameter_schema.canonicalize({})
    )
    requests = authored.dependencies().component_requests
    assert len(requests) == 1
    assert requests[0].component_id == ComponentId("volatility.true_range")


def test_atr_default_period_canonicalizes() -> None:
    authored = market_model("default_atr", when=(price.close > volatility.atr()))
    assert isinstance(authored.expression, BinaryCompareExpression)
    assert isinstance(authored.expression.right, ComponentOutputReference)
    assert authored.expression.right.parameters.get("period") == 14


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


def test_market_model_compiles_slope() -> None:
    authored = market_model(
        "positive_slope",
        when=(trend.slope(period=20) > 0),
        registry=default_mvp_registry(),
    )
    assert isinstance(authored.expression, CompareExpression)
    assert authored.expression.operator is ComparisonOperator.GT
    assert authored.expression.value == 0
    assert isinstance(authored.expression.operand, ComponentOutputReference)
    assert authored.expression.operand.component_id == ComponentId("trend.slope")
    assert authored.expression.operand.output_id == OutputId("value")
    assert authored.expression.operand.parameters.get("period") == 20
    requests = authored.dependencies().component_requests
    assert len(requests) == 1
    assert requests[0].component_id == ComponentId("trend.slope")


def test_slope_default_period_canonicalizes() -> None:
    authored = market_model("default_slope", when=(trend.slope() > 0))
    assert isinstance(authored.expression, CompareExpression)
    assert isinstance(authored.expression.operand, ComponentOutputReference)
    assert authored.expression.operand.parameters.get("period") == 20


def test_market_model_compiles_session_high() -> None:
    authored = market_model(
        "close_above_session_high",
        when=(price.close > structure.session_high()),
        registry=default_mvp_registry(),
    )
    assert isinstance(authored.expression, BinaryCompareExpression)
    assert isinstance(authored.expression.right, ComponentOutputReference)
    assert authored.expression.right.component_id == ComponentId("structure.session_range")
    assert authored.expression.right.output_id == OutputId("session_high")
    assert authored.expression.right.computation_timeframe is None
    requests = authored.dependencies().component_requests
    assert len(requests) == 1
    assert requests[0].component_id == ComponentId("structure.session_range")


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
