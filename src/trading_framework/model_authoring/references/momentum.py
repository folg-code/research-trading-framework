"""Momentum component references."""

from trading_framework.market_analysis import OutputId
from trading_framework.market_analysis.components.momentum import (
    MacdComponent,
    RsiComponent,
    StochasticComponent,
)
from trading_framework.model_authoring.references.operand import Operand
from trading_framework.model_authoring.references.timeframe import parse_timeframe
from trading_framework.model_expression.references import ComponentOutputReference
from trading_framework.time.models.timeframe import Timeframe


def rsi(
    *,
    period: int = 14,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``momentum.rsi(period=14, timeframe=None)`` -- Wilder-smoothed RSI of
    close in ``[0, 100]``, on the evaluation grid."""
    component = RsiComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({"period": period}),
            output_id=OutputId("value"),
            computation_timeframe=None if timeframe is None else parse_timeframe(timeframe),
            alias=alias,
        )
    )


def _macd_operand(
    output_id: str,
    *,
    fast_period: int,
    slow_period: int,
    signal_period: int,
    timeframe: str | Timeframe | None,
    alias: str | None,
) -> Operand:
    component = MacdComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize(
                {
                    "fast_period": fast_period,
                    "slow_period": slow_period,
                    "signal_period": signal_period,
                }
            ),
            output_id=OutputId(output_id),
            computation_timeframe=None if timeframe is None else parse_timeframe(timeframe),
            alias=alias,
        )
    )


def macd_line(
    *,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``momentum.macd_line(fast_period=12, slow_period=26, signal_period=9)``
    -- ``ema(fast_period) - ema(slow_period)``, on the evaluation grid."""
    return _macd_operand(
        "line",
        fast_period=fast_period,
        slow_period=slow_period,
        signal_period=signal_period,
        timeframe=timeframe,
        alias=alias,
    )


def macd_signal(
    *,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``momentum.macd_signal(fast_period=12, slow_period=26, signal_period=9)``
    -- the ``ema`` kernel applied to the MACD line."""
    return _macd_operand(
        "signal",
        fast_period=fast_period,
        slow_period=slow_period,
        signal_period=signal_period,
        timeframe=timeframe,
        alias=alias,
    )


def macd_histogram(
    *,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``momentum.macd_histogram(fast_period=12, slow_period=26, signal_period=9)``
    -- ``line - signal``."""
    return _macd_operand(
        "histogram",
        fast_period=fast_period,
        slow_period=slow_period,
        signal_period=signal_period,
        timeframe=timeframe,
        alias=alias,
    )


def _stochastic_operand(
    output_id: str,
    *,
    period: int,
    smoothing_period: int,
    timeframe: str | Timeframe | None,
    alias: str | None,
) -> Operand:
    component = StochasticComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize(
                {"period": period, "smoothing_period": smoothing_period}
            ),
            output_id=OutputId(output_id),
            computation_timeframe=None if timeframe is None else parse_timeframe(timeframe),
            alias=alias,
        )
    )


def stochastic_k(
    *,
    period: int = 14,
    smoothing_period: int = 3,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``momentum.stochastic_k(period=14, smoothing_period=3)`` -- %K over the
    rolling ``period``-bar high/low range, in ``[0, 100]``. A zero-range
    window yields ``50.0``, not ``0.0`` -- a deliberate divergence from the
    project's usual zero-denominator convention (D-S051-04)."""
    return _stochastic_operand(
        "k",
        period=period,
        smoothing_period=smoothing_period,
        timeframe=timeframe,
        alias=alias,
    )


def stochastic_d(
    *,
    period: int = 14,
    smoothing_period: int = 3,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``momentum.stochastic_d(period=14, smoothing_period=3)`` -- the SMA of
    %K over ``smoothing_period``."""
    return _stochastic_operand(
        "d",
        period=period,
        smoothing_period=smoothing_period,
        timeframe=timeframe,
        alias=alias,
    )
