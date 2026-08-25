"""Tests for author-facing structure.swing DSL fill-in."""

import pytest

from trading_framework.market_analysis import ComponentId, OutputId
from trading_framework.market_analysis.registry.builtins import default_mvp_registry
from trading_framework.model_authoring import LONG, market_model, price, signal_model, structure
from trading_framework.model_expression.expressions import (
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
from trading_framework.time.models.timeframe import Timeframe

_EVENT_NAMES = (
    "higher_high_event",
    "higher_low_event",
    "lower_high_event",
    "lower_low_event",
)
_LEVEL_NAMES = (
    "latest_higher_high_level",
    "latest_higher_low_level",
    "latest_lower_high_level",
    "latest_lower_low_level",
)
_INTERNAL_NAMES = (
    "swing_high_observed_index",
    "latest_higher_low_observed_index",
    "latest_higher_high_observed_index",
)


@pytest.mark.parametrize("name", _EVENT_NAMES)
def test_structure_events_compile_as_on_event_signals(name: str) -> None:
    operand = getattr(structure, name)(pivot_range=15, timeframe="5m")
    authored = signal_model(name, direction=LONG, when=operand, registry=default_mvp_registry())

    assert authored.definition.firing_policy is SignalFiringPolicy.ON_EVENT
    assert isinstance(authored.expression, CompareExpression)
    assert authored.expression.operator is ComparisonOperator.EQ
    assert authored.expression.value is True
    assert isinstance(authored.expression.operand, ComponentOutputReference)
    assert authored.expression.operand.component_id == ComponentId("structure.swing")
    assert authored.expression.operand.output_id == OutputId(name)
    assert authored.expression.operand.computation_timeframe == Timeframe("5m")
    assert authored.expression.operand.parameters.get("pivot_range") == 15
    requests = authored.dependencies().component_requests
    assert len(requests) == 1
    assert requests[0].component_id == ComponentId("structure.swing")


@pytest.mark.parametrize("name", _LEVEL_NAMES)
def test_structure_latest_levels_compile_as_market_compares(name: str) -> None:
    operand = getattr(structure, name)(pivot_range=15, timeframe="5m")
    authored = market_model(
        name,
        when=(price.close > operand),
        registry=default_mvp_registry(),
    )

    assert isinstance(authored.expression, BinaryCompareExpression)
    assert authored.expression.operator is ComparisonOperator.GT
    assert authored.expression.left == MarketFieldReference(field=MarketField.CLOSE)
    assert isinstance(authored.expression.right, ComponentOutputReference)
    assert authored.expression.right.component_id == ComponentId("structure.swing")
    assert authored.expression.right.output_id == OutputId(name)
    assert authored.expression.right.computation_timeframe == Timeframe("5m")
    assert authored.expression.right.parameters.get("pivot_range") == 15


@pytest.mark.parametrize("name", _INTERNAL_NAMES)
def test_observed_index_outputs_are_not_on_structure_namespace(name: str) -> None:
    assert not hasattr(structure, name)
