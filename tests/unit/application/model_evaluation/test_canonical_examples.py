"""Tests for canonical Sprint 006 model examples."""

from trading_framework.application.model_evaluation.canonical_examples import (
    CANONICAL_COMBINED_SIGNAL_ID,
    CANONICAL_MARKET_MODEL_ID,
    CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID,
    CANONICAL_SIGNAL_HIGHER_LOW_ID,
    build_canonical_combined_signal,
    build_canonical_market_model_high_volatility,
    build_canonical_model_bundle,
    build_canonical_signal_high_volatility_on_true_edge,
    build_canonical_signal_higher_low_on_event,
)
from trading_framework.market_analysis.registry.builtins import default_mvp_registry
from trading_framework.model_expression.expressions import AndExpression, CompareExpression
from trading_framework.model_expression.validation import validate_expression
from trading_framework.signal_model import SignalDirection, SignalFiringPolicy


def test_canonical_market_model_validates() -> None:
    definition = build_canonical_market_model_high_volatility()
    registry = default_mvp_registry()

    validate_expression(definition.expression, registry)

    assert definition.market_model_id == CANONICAL_MARKET_MODEL_ID
    assert isinstance(definition.expression, CompareExpression)


def test_canonical_signal_models_validate() -> None:
    registry = default_mvp_registry()
    event_signal = build_canonical_signal_higher_low_on_event()
    edge_signal = build_canonical_signal_high_volatility_on_true_edge()
    combined_signal = build_canonical_combined_signal()

    validate_expression(event_signal.expression, registry)
    validate_expression(edge_signal.expression, registry)
    validate_expression(combined_signal.expression, registry)

    assert event_signal.signal_model_id == CANONICAL_SIGNAL_HIGHER_LOW_ID
    assert event_signal.firing_policy is SignalFiringPolicy.ON_EVENT
    assert event_signal.direction is SignalDirection.LONG

    assert edge_signal.signal_model_id == CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID
    assert edge_signal.firing_policy is SignalFiringPolicy.ON_TRUE_EDGE

    assert combined_signal.signal_model_id == CANONICAL_COMBINED_SIGNAL_ID
    assert isinstance(combined_signal.expression, AndExpression)


def test_canonical_model_bundle_contains_all_examples() -> None:
    bundle = build_canonical_model_bundle()

    assert len(bundle.market_models) == 1
    assert len(bundle.signal_models) == 3
    assert bundle.market_models[0].market_model_id == CANONICAL_MARKET_MODEL_ID
    signal_ids = {definition.signal_model_id for definition in bundle.signal_models}
    assert signal_ids == {
        CANONICAL_SIGNAL_HIGHER_LOW_ID,
        CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID,
        CANONICAL_COMBINED_SIGNAL_ID,
    }
