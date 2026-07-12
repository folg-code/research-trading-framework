"""Step-by-step declarative model examples for spike scripts and local iteration."""

from dataclasses import dataclass

from trading_framework.market_analysis import OutputId
from trading_framework.market_analysis.components.structure import SwingStructureComponent
from trading_framework.market_analysis.components.trend import EmaComponent
from trading_framework.market_analysis.components.volatility import VolatilityStateComponent
from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.model_expression.expressions import (
    AndExpression,
    CompareExpression,
    ComparisonOperator,
)
from trading_framework.model_expression.references import (
    ComponentOutputReference,
    MarketField,
    MarketFieldReference,
)
from trading_framework.signal_model.definitions import (
    SignalDirection,
    SignalFiringPolicy,
    SignalModelDefinition,
)
from trading_framework.time.models.timeframe import Timeframe

DEFAULT_SWING_TIMEFRAME = Timeframe("5m")


def component_output_reference(
    component: VolatilityStateComponent | EmaComponent | SwingStructureComponent,
    *,
    parameters: dict[str, object],
    output_id: str,
    computation_timeframe: Timeframe | None = None,
    alias: str | None = None,
) -> ComponentOutputReference:
    """Build one ``ComponentOutputReference`` from a live component instance."""
    return ComponentOutputReference(
        component_id=component.component_id,
        parameters=component.parameter_schema.canonicalize(parameters),
        output_id=OutputId(output_id),
        computation_timeframe=computation_timeframe,
        alias=alias,
    )


def build_volatility_state_market_model(
    *,
    market_model_id: str = "high_volatility",
    period: int = 14,
    threshold: float = 2.0,
) -> MarketModelDefinition:
    """Market Model: ``volatility.state == 1``."""
    component = VolatilityStateComponent()
    return MarketModelDefinition(
        market_model_id=market_model_id,
        expression=CompareExpression(
            operand=component_output_reference(
                component,
                parameters={"period": period, "threshold": threshold},
                output_id="state",
            ),
            operator=ComparisonOperator.EQ,
            value=1.0,
        ),
    )


def build_close_above_threshold_market_model(
    *,
    market_model_id: str = "close_above_threshold",
    threshold: float = 100.0,
) -> MarketModelDefinition:
    """Market Model: ``close > threshold`` using ``MarketFieldReference``."""
    return MarketModelDefinition(
        market_model_id=market_model_id,
        expression=CompareExpression(
            operand=MarketFieldReference(field=MarketField.CLOSE),
            operator=ComparisonOperator.GT,
            value=threshold,
        ),
    )


def ema_value_reference(*, period: int = 20, alias: str | None = "ema") -> ComponentOutputReference:
    """Reference EMA — add to expressions so ``evaluate_models`` loads the column."""
    return component_output_reference(
        EmaComponent(),
        parameters={"period": period},
        output_id="value",
        alias=alias,
    )


def build_higher_low_signal_model(
    *,
    signal_model_id: str = "higher_low_long",
    pivot_range: int = 15,
    computation_timeframe: Timeframe = DEFAULT_SWING_TIMEFRAME,
) -> SignalModelDefinition:
    """Signal Model: ``structure.swing.higher_low_event == true`` with ``ON_EVENT``."""
    return SignalModelDefinition(
        signal_model_id=signal_model_id,
        expression=CompareExpression(
            operand=component_output_reference(
                SwingStructureComponent(),
                parameters={"pivot_range": pivot_range},
                output_id="higher_low_event",
                computation_timeframe=computation_timeframe,
            ),
            operator=ComparisonOperator.EQ,
            value=True,
        ),
        direction=SignalDirection.LONG,
        firing_policy=SignalFiringPolicy.ON_EVENT,
    )


def build_volatility_edge_signal_model(
    *,
    signal_model_id: str = "high_volatility_edge",
    period: int = 14,
    threshold: float = 2.0,
) -> SignalModelDefinition:
    """Signal Model: ``volatility.state == 1`` with ``ON_TRUE_EDGE``."""
    return SignalModelDefinition(
        signal_model_id=signal_model_id,
        expression=CompareExpression(
            operand=component_output_reference(
                VolatilityStateComponent(),
                parameters={"period": period, "threshold": threshold},
                output_id="state",
            ),
            operator=ComparisonOperator.EQ,
            value=1.0,
        ),
        direction=SignalDirection.LONG,
        firing_policy=SignalFiringPolicy.ON_TRUE_EDGE,
    )


def build_combined_volatility_and_higher_low_signal(
    *,
    signal_model_id: str = "high_vol_and_higher_low",
    period: int = 14,
    threshold: float = 2.0,
    pivot_range: int = 15,
    computation_timeframe: Timeframe = DEFAULT_SWING_TIMEFRAME,
) -> SignalModelDefinition:
    """Signal Model: ``volatility.state == 1 AND higher_low_event == true``."""
    return SignalModelDefinition(
        signal_model_id=signal_model_id,
        expression=AndExpression(
            left=CompareExpression(
                operand=component_output_reference(
                    VolatilityStateComponent(),
                    parameters={"period": period, "threshold": threshold},
                    output_id="state",
                ),
                operator=ComparisonOperator.EQ,
                value=1.0,
            ),
            right=CompareExpression(
                operand=component_output_reference(
                    SwingStructureComponent(),
                    parameters={"pivot_range": pivot_range},
                    output_id="higher_low_event",
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
class ExampleModelBundle:
    """Example models tuned for the S005 vertical slice fixture."""

    market_models: tuple[MarketModelDefinition, ...]
    signal_models: tuple[SignalModelDefinition, ...]


def build_example_model_bundle() -> ExampleModelBundle:
    """Default bundle for ``run_build_declarative_models_example.py``."""
    return ExampleModelBundle(
        market_models=(
            build_volatility_state_market_model(threshold=2.0),
            build_close_above_threshold_market_model(threshold=1278.0),
        ),
        signal_models=(
            build_higher_low_signal_model(),
            build_volatility_edge_signal_model(threshold=2.0),
            build_combined_volatility_and_higher_low_signal(threshold=2.0),
        ),
    )
