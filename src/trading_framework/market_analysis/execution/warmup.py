"""Extend computation range for warm-up history requirements."""

from datetime import timedelta

from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.market_analysis.planning.plan import ExecutionPlan, PlannedNode
from trading_framework.time.models.timeframe import Timeframe


def _source_bars_for_component(node: PlannedNode, *, source_timeframe: Timeframe) -> int:
    warmup_bars = node.component.history_requirement(node.request.parameters).bars_before
    if warmup_bars <= 0:
        return 0
    computation_timeframe = node.computation_identity.computation_timeframe
    ratio = computation_timeframe.total_seconds // source_timeframe.total_seconds
    if ratio <= 0:
        return warmup_bars
    return warmup_bars * ratio


def max_history_requirement(plan: ExecutionPlan, *, source_timeframe: Timeframe) -> int:
    component_nodes = plan.component_nodes()
    if not component_nodes:
        return 0
    return max(
        _source_bars_for_component(node, source_timeframe=source_timeframe)
        for node in component_nodes
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
