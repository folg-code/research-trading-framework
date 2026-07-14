"""Tests for Signal Model evaluation and firing."""

from collections.abc import Callable

from trading_framework.market_analysis import OutputId
from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.market_analysis.components.structure import SwingStructureComponent
from trading_framework.market_analysis.components.volatility import VolatilityStateComponent
from trading_framework.model_expression import (
    CompareExpression,
    ComparisonOperator,
    ComponentOutputReference,
)
from trading_framework.signal_model import (
    SignalDirection,
    SignalFiringPolicy,
    SignalModelDefinition,
    SignalModelEvaluator,
    apply_firing_policy,
)
from trading_framework.time.models.timeframe import Timeframe


def test_signal_model_condition_is_dense(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    component = VolatilityStateComponent()
    frame = build_test_frame(columns={"vol_state": (0.0, 1.0, 1.0, 0.0)})
    definition = SignalModelDefinition(
        signal_model_id="high_vol_signal",
        expression=CompareExpression(
            operand=ComponentOutputReference(
                component_id=component.component_id,
                parameters=component.parameter_schema.canonicalize(
                    {"period": 14, "threshold": 5.0}
                ),
                output_id=OutputId("state"),
                alias="vol_state",
            ),
            operator=ComparisonOperator.EQ,
            value=1.0,
        ),
        direction=SignalDirection.LONG,
        firing_policy=SignalFiringPolicy.ON_TRUE_EDGE,
    )

    condition = SignalModelEvaluator().evaluate_condition(
        definition,
        frame,
        evaluation_timeframe=Timeframe("1m"),
    )

    assert condition["condition_met"].to_list() == [False, True, True, False]


def test_on_true_edge_emits_once_for_state_condition(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    component = VolatilityStateComponent()
    frame = build_test_frame(columns={"vol_state": (0.0, 1.0, 1.0, 1.0, 0.0)})
    definition = SignalModelDefinition(
        signal_model_id="high_vol_edge",
        expression=CompareExpression(
            operand=ComponentOutputReference(
                component_id=component.component_id,
                parameters=component.parameter_schema.canonicalize(
                    {"period": 14, "threshold": 5.0}
                ),
                output_id=OutputId("state"),
                alias="vol_state",
            ),
            operator=ComparisonOperator.EQ,
            value=1.0,
        ),
        direction=SignalDirection.NEUTRAL,
        firing_policy=SignalFiringPolicy.ON_TRUE_EDGE,
    )

    emissions = SignalModelEvaluator().evaluate_emissions(
        definition,
        frame,
        evaluation_timeframe=Timeframe("1m"),
    )

    assert emissions.height == 1
    assert emissions["detected_at"][0] == frame.timestamps[1]
    assert emissions["direction"][0] == "neutral"
    assert emissions["firing_policy"][0] == "on_true_edge"


def test_on_event_emits_on_sparse_event_bar(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    component = SwingStructureComponent()
    frame = build_test_frame(
        columns={"higher_low_event": (0.0, 0.0, 1.0, 0.0, 0.0)},
    )
    definition = SignalModelDefinition(
        signal_model_id="higher_low",
        expression=CompareExpression(
            operand=ComponentOutputReference(
                component_id=component.component_id,
                parameters=component.parameter_schema.canonicalize({"pivot_range": 15}),
                output_id=OutputId("higher_low_event"),
                alias="higher_low_event",
            ),
            operator=ComparisonOperator.EQ,
            value=True,
        ),
        direction=SignalDirection.LONG,
        firing_policy=SignalFiringPolicy.ON_EVENT,
    )

    emissions = SignalModelEvaluator().evaluate_emissions(
        definition,
        frame,
        evaluation_timeframe=Timeframe("1m"),
    )

    assert emissions.height == 1
    assert emissions["detected_at"][0] == frame.timestamps[2]
    assert emissions["direction"][0] == "long"


def test_evaluate_emissions_reuses_precomputed_condition(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    component = SwingStructureComponent()
    frame = build_test_frame(columns={"higher_low_event": (0.0, 0.0, 1.0, 0.0, 0.0)})
    definition = SignalModelDefinition(
        signal_model_id="higher_low",
        expression=CompareExpression(
            operand=ComponentOutputReference(
                component_id=component.component_id,
                parameters=component.parameter_schema.canonicalize({"pivot_range": 15}),
                output_id=OutputId("higher_low_event"),
                alias="higher_low_event",
            ),
            operator=ComparisonOperator.EQ,
            value=True,
        ),
        direction=SignalDirection.LONG,
        firing_policy=SignalFiringPolicy.ON_EVENT,
    )
    evaluator = SignalModelEvaluator()
    condition = evaluator.evaluate_condition(
        definition,
        frame,
        evaluation_timeframe=Timeframe("1m"),
    )
    emissions = evaluator.evaluate_emissions(
        definition,
        frame,
        evaluation_timeframe=Timeframe("1m"),
        condition=condition,
    )

    assert emissions.height == 1
    assert emissions["detected_at"][0] == frame.timestamps[2]


def test_null_condition_does_not_fire() -> None:
    import polars as pl

    mask = apply_firing_policy(
        pl.Series([None, True]),
        policy=SignalFiringPolicy.ON_TRUE_EDGE,
    )
    assert mask.to_list() == [False, True]
