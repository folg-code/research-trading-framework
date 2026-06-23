"""Extend computation range for warm-up history requirements."""

from datetime import timedelta

from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.market_analysis.planning.plan import ExecutionPlan
from trading_framework.time.models.timeframe import Timeframe


def max_history_requirement(plan: ExecutionPlan) -> int:
    if not plan.nodes:
        return 0
    return max(
        node.component.history_requirement(node.request.parameters).bars_before
        for node in plan.nodes
    )


def extend_computation_range(
    requested_range: TimeRange,
    *,
    warmup_bars: int,
    timeframe: Timeframe,
) -> TimeRange:
    if warmup_bars <= 0:
        return requested_range
    delta = timedelta(seconds=timeframe.total_seconds * warmup_bars)
    return TimeRange(
        start=requested_range.start - delta,
        end=requested_range.end,
    )
