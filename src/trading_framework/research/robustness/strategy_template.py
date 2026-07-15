"""Strategy template builders for robustness parameter sweeps."""

from __future__ import annotations

from decimal import Decimal

from trading_framework.application.model_evaluation.canonical_examples import (
    CANONICAL_SWING_PIVOT_RANGE,
    CANONICAL_VOLATILITY_PERIOD,
    CANONICAL_VOLATILITY_THRESHOLD,
    build_canonical_market_model_high_volatility,
    build_canonical_signal_higher_low_on_event,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.strategy.canonical_examples import (
    CANONICAL_EXIT_AFTER_BARS,
    CANONICAL_POSITION_QUANTITY,
    CANONICAL_STRATEGY_MODEL_ID,
)
from trading_framework.strategy.exit_model import FixedBarsExitModel
from trading_framework.strategy.risk_model import FixedQuantityRiskModel
from trading_framework.strategy.strategy_model import StrategyModelDefinition

CANONICAL_STRATEGY_TEMPLATE_ID = CANONICAL_STRATEGY_MODEL_ID

_ALLOWED_OVERRIDE_KEYS = frozenset(
    {
        "exit_after_bars",
        "volatility_threshold",
        "volatility_period",
        "pivot_range",
    }
)


def build_strategy_model_from_cell(
    *,
    template_id: str,
    parameter_overrides: dict[str, str],
) -> StrategyModelDefinition:
    """Materialize one Strategy Model from a canonical template and overrides."""
    if template_id != CANONICAL_STRATEGY_TEMPLATE_ID:
        msg = f"unsupported strategy template: {template_id}"
        raise ValidationError(msg)
    unknown = set(parameter_overrides) - _ALLOWED_OVERRIDE_KEYS
    if unknown:
        msg = f"unsupported parameter overrides: {sorted(unknown)}"
        raise ValidationError(msg)

    exit_after_bars = _parse_int_override(
        parameter_overrides,
        key="exit_after_bars",
        default=CANONICAL_EXIT_AFTER_BARS,
        minimum=1,
    )
    volatility_threshold = _parse_float_override(
        parameter_overrides,
        key="volatility_threshold",
        default=CANONICAL_VOLATILITY_THRESHOLD,
        minimum=0.0,
    )
    volatility_period = _parse_int_override(
        parameter_overrides,
        key="volatility_period",
        default=CANONICAL_VOLATILITY_PERIOD,
        minimum=1,
    )
    pivot_range = _parse_int_override(
        parameter_overrides,
        key="pivot_range",
        default=CANONICAL_SWING_PIVOT_RANGE,
        minimum=1,
    )

    return StrategyModelDefinition(
        strategy_model_id=CANONICAL_STRATEGY_MODEL_ID,
        market_model=build_canonical_market_model_high_volatility(
            period=volatility_period,
            threshold=volatility_threshold,
        ),
        signal_model=build_canonical_signal_higher_low_on_event(pivot_range=pivot_range),
        exit_model=FixedBarsExitModel(exit_after_bars=exit_after_bars),
        risk_model=FixedQuantityRiskModel(quantity=Decimal(CANONICAL_POSITION_QUANTITY)),
    )


def _parse_int_override(
    overrides: dict[str, str],
    *,
    key: str,
    default: int,
    minimum: int,
) -> int:
    raw = overrides.get(key)
    if raw is None:
        return default
    value = int(raw)
    if value < minimum:
        msg = f"{key} must be >= {minimum}"
        raise ValidationError(msg)
    return value


def _parse_float_override(
    overrides: dict[str, str],
    *,
    key: str,
    default: float,
    minimum: float,
) -> float:
    raw = overrides.get(key)
    if raw is None:
        return default
    value = float(raw)
    if value < minimum:
        msg = f"{key} must be >= {minimum}"
        raise ValidationError(msg)
    return value
