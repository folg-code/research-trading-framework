"""Live signal evaluation adapters for dry-run execution."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import final

import numpy as np

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis.adapters.numpy.kernels import ema
from trading_framework.model_expression.expressions import (
    BinaryCompareExpression,
    ComparisonOperator,
)
from trading_framework.model_expression.references import (
    ComponentOutputReference,
    MarketField,
    MarketFieldReference,
)
from trading_framework.signal_model import SignalFiringPolicy
from trading_framework.strategy import StrategyModelDefinition, validate_strategy_model_definition

EMA_COMPONENT_ID = "trend.ema"
EMA_OUTPUT_ID = "value"


@final
@dataclass(frozen=True, slots=True)
class LiveSignalEvaluation:
    """Evaluated live signal booleans for one runtime decision step."""

    entry_signal_active: bool
    exit_signal_active: bool
    condition_active: bool
    close: float
    ema_value: float | None


@final
@dataclass(frozen=True, slots=True)
class EmaMomentumLiveSignalEvaluator:
    """Evaluate the supported close-above-EMA Strategy Model on closed bars."""

    strategy_model: StrategyModelDefinition

    def __post_init__(self) -> None:
        validate_strategy_model_definition(self.strategy_model)
        _extract_ema_period(self.strategy_model)

    def evaluate(self, closed_bars: Sequence[MarketBar]) -> LiveSignalEvaluation:
        """Evaluate the latest closed bar against the shared Strategy Model."""
        if not closed_bars:
            msg = "closed_bars must contain at least one bar"
            raise ValidationError(msg)
        period = _extract_ema_period(self.strategy_model)
        closes = np.asarray([float(bar.close.value) for bar in closed_bars], dtype=np.float64)
        ema_values = ema(closes, period)
        latest_close = float(closes[-1])
        latest_ema = float(ema_values[-1]) if not np.isnan(ema_values[-1]) else None
        latest_condition = latest_ema is not None and latest_close > latest_ema
        previous_condition = _previous_condition(closes, ema_values)
        entry_signal = _fires_on_true_edge(
            latest_condition=latest_condition,
            previous_condition=previous_condition,
            firing_policy=self.strategy_model.signal_model.firing_policy,
        )
        return LiveSignalEvaluation(
            entry_signal_active=entry_signal,
            exit_signal_active=False,
            condition_active=latest_condition,
            close=latest_close,
            ema_value=latest_ema,
        )


def _previous_condition(
    closes: np.ndarray,
    ema_values: np.ndarray,
) -> bool | None:
    if closes.size < 2 or np.isnan(ema_values[-2]):
        return None
    return bool(closes[-2] > ema_values[-2])


def _fires_on_true_edge(
    *,
    latest_condition: bool,
    previous_condition: bool | None,
    firing_policy: SignalFiringPolicy,
) -> bool:
    if firing_policy is not SignalFiringPolicy.ON_TRUE_EDGE:
        msg = "live EMA momentum evaluator supports ON_TRUE_EDGE signals only"
        raise ValidationError(msg)
    if not latest_condition:
        return False
    return previous_condition is None or previous_condition is False


def _extract_ema_period(strategy_model: StrategyModelDefinition) -> int:
    expression = strategy_model.signal_model.expression
    if not isinstance(expression, BinaryCompareExpression):
        msg = "live EMA momentum evaluator requires a binary compare signal expression"
        raise ValidationError(msg)
    if expression.operator is not ComparisonOperator.GT:
        msg = "live EMA momentum evaluator requires a close > EMA expression"
        raise ValidationError(msg)
    if (
        not isinstance(expression.left, MarketFieldReference)
        or expression.left.field is not MarketField.CLOSE
    ):
        msg = "live EMA momentum evaluator requires close as the left operand"
        raise ValidationError(msg)
    right = expression.right
    if not isinstance(right, ComponentOutputReference):
        msg = "live EMA momentum evaluator requires EMA as the right operand"
        raise ValidationError(msg)
    if str(right.component_id) != EMA_COMPONENT_ID or str(right.output_id) != EMA_OUTPUT_ID:
        msg = "live EMA momentum evaluator requires trend.ema value as the right operand"
        raise ValidationError(msg)
    return int(right.parameters.get("period"))
