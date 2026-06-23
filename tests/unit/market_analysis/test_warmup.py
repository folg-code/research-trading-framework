"""Warm-up range extension tests."""

from datetime import UTC, datetime

from trading_framework.market_analysis.execution.warmup import (
    extend_computation_range,
    max_history_requirement,
)
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.time.models.timeframe import Timeframe


def test_extend_computation_range_shifts_start_by_timeframe_bars() -> None:
    requested = TimeRange(
        start=datetime(2024, 1, 1, 12, 10, tzinfo=UTC),
        end=datetime(2024, 1, 1, 13, 0, tzinfo=UTC),
    )
    extended = extend_computation_range(
        requested,
        warmup_bars=3,
        timeframe=Timeframe("1m"),
    )
    assert extended.start == datetime(2024, 1, 1, 12, 7, tzinfo=UTC)
    assert extended.end == requested.end


def test_max_history_requirement_returns_zero_for_empty_plan() -> None:
    from trading_framework.market_analysis.planning.plan import ExecutionPlan

    assert max_history_requirement(ExecutionPlan(nodes=())) == 0
