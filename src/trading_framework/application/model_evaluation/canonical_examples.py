"""Canonical Sprint 006 Market and Signal Model examples for tests and inspection."""

from dataclasses import dataclass

from trading_framework.market_analysis import OutputId
from trading_framework.market_analysis.components.structure import SwingStructureComponent
from trading_framework.market_analysis.components.volatility import VolatilityStateComponent
from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.model_expression.expressions import (
    AndExpression,
    CompareExpression,
    ComparisonOperator,
)
from trading_framework.model_expression.references import ComponentOutputReference
from trading_framework.signal_model.definitions import (
    SignalDirection,
    SignalFiringPolicy,
    SignalModelDefinition,
)
from trading_framework.time.models.timeframe import Timeframe

CANONICAL_VOLATILITY_PERIOD = 14
CANONICAL_VOLATILITY_THRESHOLD = 5.0
CANONICAL_SWING_PIVOT_RANGE = 15
CANONICAL_SWING_COMPUTATION_TIMEFRAME = Timeframe("5m")

CANONICAL_MARKET_MODEL_ID = "high_volatility"
CANONICAL_SIGNAL_HIGHER_LOW_ID = "higher_low_long"
CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID = "high_volatility_long_edge"
CANONICAL_COMBINED_SIGNAL_ID = "high_vol_and_higher_low"


def volatility_state_reference(
    *,
    period: int = CANONICAL_VOLATILITY_PERIOD,
    threshold: float = CANONICAL_VOLATILITY_THRESHOLD,
    alias: str | None = None,
) -> ComponentOutputReference:
    """Reference to canonical ``volatility.state`` output on the evaluation grid."""
    component = VolatilityStateComponent()
    return ComponentOutputReference(
        component_id=component.component_id,
        parameters=component.parameter_schema.canonicalize(
            {"period": period, "threshold": threshold}
        ),
        output_id=OutputId("state"),
        alias=alias,
    )


def swing_higher_low_event_reference(
    *,
    pivot_range: int = CANONICAL_SWING_PIVOT_RANGE,
    computation_timeframe: Timeframe = CANONICAL_SWING_COMPUTATION_TIMEFRAME,
    alias: str | None = None,
) -> ComponentOutputReference:
    """Reference to canonical ``structure.swing.higher_low_event`` output."""
    component = SwingStructureComponent()
    return ComponentOutputReference(
        component_id=component.component_id,
        parameters=component.parameter_schema.canonicalize({"pivot_range": pivot_range}),
        output_id=OutputId("higher_low_event"),
        computation_timeframe=computation_timeframe,
        alias=alias,
    )


def build_canonical_market_model_high_volatility(
    *,
    market_model_id: str = CANONICAL_MARKET_MODEL_ID,
    period: int = CANONICAL_VOLATILITY_PERIOD,
    threshold: float = CANONICAL_VOLATILITY_THRESHOLD,
) -> MarketModelDefinition:
    """Market Model: ``volatility.state == 1`` (dense high-volatility state)."""
    return MarketModelDefinition(
        market_model_id=market_model_id,
        expression=CompareExpression(
            operand=volatility_state_reference(period=period, threshold=threshold),
            operator=ComparisonOperator.EQ,
            value=1.0,
        ),
    )


def build_canonical_signal_higher_low_on_event(
    *,
    signal_model_id: str = CANONICAL_SIGNAL_HIGHER_LOW_ID,
    pivot_range: int = CANONICAL_SWING_PIVOT_RANGE,
    computation_timeframe: Timeframe = CANONICAL_SWING_COMPUTATION_TIMEFRAME,
) -> SignalModelDefinition:
    """Signal Model: ``structure.swing.higher_low_event == true`` with ``ON_EVENT``."""
    return SignalModelDefinition(
        signal_model_id=signal_model_id,
        expression=CompareExpression(
            operand=swing_higher_low_event_reference(
                pivot_range=pivot_range,
                computation_timeframe=computation_timeframe,
            ),
            operator=ComparisonOperator.EQ,
            value=True,
        ),
        direction=SignalDirection.LONG,
        firing_policy=SignalFiringPolicy.ON_EVENT,
    )


def build_canonical_signal_high_volatility_on_true_edge(
    *,
    signal_model_id: str = CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID,
    period: int = CANONICAL_VOLATILITY_PERIOD,
    threshold: float = CANONICAL_VOLATILITY_THRESHOLD,
    direction: SignalDirection = SignalDirection.LONG,
) -> SignalModelDefinition:
    """Signal Model: ``volatility.state == 1`` with ``ON_TRUE_EDGE``."""
    return SignalModelDefinition(
        signal_model_id=signal_model_id,
        expression=CompareExpression(
            operand=volatility_state_reference(period=period, threshold=threshold),
            operator=ComparisonOperator.EQ,
            value=1.0,
        ),
        direction=direction,
        firing_policy=SignalFiringPolicy.ON_TRUE_EDGE,
    )


def build_canonical_combined_signal(
    *,
    signal_model_id: str = CANONICAL_COMBINED_SIGNAL_ID,
    period: int = CANONICAL_VOLATILITY_PERIOD,
    threshold: float = CANONICAL_VOLATILITY_THRESHOLD,
    pivot_range: int = CANONICAL_SWING_PIVOT_RANGE,
    computation_timeframe: Timeframe = CANONICAL_SWING_COMPUTATION_TIMEFRAME,
) -> SignalModelDefinition:
    """Signal Model: ``volatility.state == 1 AND higher_low_event == true``."""
    return SignalModelDefinition(
        signal_model_id=signal_model_id,
        expression=AndExpression(
            left=CompareExpression(
                operand=volatility_state_reference(period=period, threshold=threshold),
                operator=ComparisonOperator.EQ,
                value=1.0,
            ),
            right=CompareExpression(
                operand=swing_higher_low_event_reference(
                    pivot_range=pivot_range,
                    computation_timeframe=computation_timeframe,
                ),
                operator=ComparisonOperator.EQ,
                value=True,
            ),
        ),
        direction=SignalDirection.LONG,
        firing_policy=SignalFiringPolicy.ON_EVENT,
    )


@dataclass(frozen=True, slots=True)
class CanonicalModelBundle:
    """All canonical Sprint 006 examples for one vertical slice."""

    market_models: tuple[MarketModelDefinition, ...]
    signal_models: tuple[SignalModelDefinition, ...]


def build_canonical_model_bundle() -> CanonicalModelBundle:
    """Build the full canonical example set used by integration and inspection."""
    return CanonicalModelBundle(
        market_models=(build_canonical_market_model_high_volatility(),),
        signal_models=(
            build_canonical_signal_higher_low_on_event(),
            build_canonical_signal_high_volatility_on_true_edge(),
            build_canonical_combined_signal(),
        ),
    )
