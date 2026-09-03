"""Statistics/regime component references."""

from trading_framework.market_analysis import OutputId
from trading_framework.market_analysis.components.statistics import (
    ReturnAutocorrelationComponent,
    ReturnDistributionComponent,
)
from trading_framework.model_authoring.references.operand import Operand
from trading_framework.model_authoring.references.timeframe import parse_timeframe
from trading_framework.model_expression.references import ComponentOutputReference
from trading_framework.time.models.timeframe import Timeframe


def return_autocorrelation(
    *,
    period: int = 60,
    lag: int = 1,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``statistics.return_autocorrelation(period=60, lag=1)`` -- rolling
    population Pearson correlation between log returns and their own
    lag-``lag`` shift, computed within each ``period``-bar window, in
    ``[-1, 1]``, on the evaluation grid. A degenerate (zero-variance) window
    yields ``0.0`` (D-S051-04/05)."""
    component = ReturnAutocorrelationComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({"period": period, "lag": lag}),
            output_id=OutputId("value"),
            computation_timeframe=None if timeframe is None else parse_timeframe(timeframe),
            alias=alias,
        )
    )


def return_skew(
    *,
    period: int = 60,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``statistics.return_skew(period=60)`` -- rolling population
    Fisher-Pearson skewness of log returns over each ``period``-bar window,
    on the evaluation grid. A zero-variance (flat) window yields ``0.0``
    (D-S051-04/05). Short windows on 1m bars are outlier-dominated -- see
    ``ReturnDistributionComponent``'s docstring."""
    component = ReturnDistributionComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({"period": period}),
            output_id=OutputId("skew"),
            computation_timeframe=None if timeframe is None else parse_timeframe(timeframe),
            alias=alias,
        )
    )


def return_excess_kurtosis(
    *,
    period: int = 60,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``statistics.return_excess_kurtosis(period=60)`` -- rolling population
    Fisher-Pearson excess kurtosis of log returns over each ``period``-bar
    window, on the evaluation grid. A zero-variance (flat) window yields
    ``0.0`` (D-S051-04/05). Short windows on 1m bars are outlier-dominated --
    see ``ReturnDistributionComponent``'s docstring."""
    component = ReturnDistributionComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({"period": period}),
            output_id=OutputId("excess_kurtosis"),
            computation_timeframe=None if timeframe is None else parse_timeframe(timeframe),
            alias=alias,
        )
    )
