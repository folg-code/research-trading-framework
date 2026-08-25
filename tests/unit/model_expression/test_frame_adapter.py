"""Unit tests for vectorized evaluation-table construction."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone

import numpy as np
import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.temporal import derive_bar_interval
from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.model_expression.evaluation.frame_adapter import (
    build_evaluation_dataframe,
)
from trading_framework.time.models.timeframe import Timeframe


def _frame(
    *,
    timestamps: tuple[datetime, ...],
    columns: dict[str, tuple[float, ...]],
) -> AnalysisFrame:
    return AnalysisFrame(timestamps=timestamps, columns=columns, column_lineage={})


def test_available_at_matches_derive_bar_interval_for_1m_and_5m(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    frame = build_test_frame(columns={"close": (1.0, 2.0, 3.0)})
    for timeframe in (Timeframe("1m"), Timeframe("5m")):
        table = build_evaluation_dataframe(
            frame,
            evaluation_timeframe=timeframe,
            column_keys=("close",),
        )
        expected_starts = [
            derive_bar_interval(timestamp, timeframe)[0] for timestamp in frame.timestamps
        ]
        expected_available = [
            derive_bar_interval(timestamp, timeframe)[1] for timestamp in frame.timestamps
        ]
        assert table["timestamp"].to_list() == expected_starts
        assert table["available_at"].to_list() == expected_available
        assert getattr(table["timestamp"].dtype, "time_zone", None) == "UTC"
        assert getattr(table["available_at"].dtype, "time_zone", None) == "UTC"


def test_operand_columns_match_source_frame_tuples(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    close = (1.0, float("nan"), 3.0)
    volume = (10.0, 20.0, 30.0)
    frame = build_test_frame(columns={"close": close, "volume": volume})
    table = build_evaluation_dataframe(
        frame,
        evaluation_timeframe=Timeframe("1m"),
        column_keys=("volume", "close"),
    )
    assert table.columns == ["timestamp", "available_at", "volume", "close"]
    assert table.height == len(frame.timestamps)
    np.testing.assert_array_equal(table["close"].to_numpy(), np.asarray(close, dtype=np.float64))
    np.testing.assert_array_equal(table["volume"].to_numpy(), np.asarray(volume, dtype=np.float64))


def test_empty_column_keys_still_yields_timestamp_and_available_at(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    frame = build_test_frame(columns={"close": (1.0, 2.0)})
    table = build_evaluation_dataframe(
        frame,
        evaluation_timeframe=Timeframe("1m"),
        column_keys=(),
    )
    assert table.columns == ["timestamp", "available_at"]
    assert table.height == 2
    expected = [
        derive_bar_interval(timestamp, Timeframe("1m"))[1] for timestamp in frame.timestamps
    ]
    assert table["available_at"].to_list() == expected


def test_empty_timestamps_yield_empty_utc_timestamp_and_available_at() -> None:
    frame = _frame(timestamps=(), columns={})
    table = build_evaluation_dataframe(
        frame,
        evaluation_timeframe=Timeframe("1m"),
        column_keys=(),
    )
    assert table.columns == ["timestamp", "available_at"]
    assert table.height == 0
    assert getattr(table["timestamp"].dtype, "time_zone", None) == "UTC"
    assert getattr(table["available_at"].dtype, "time_zone", None) == "UTC"


def test_source_analysis_frame_is_not_mutated(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    close = (1.0, 2.0, 3.0)
    frame = build_test_frame(columns={"close": close})
    timestamps_before = frame.timestamps
    columns_before = frame.columns
    close_before = frame.columns["close"]
    build_evaluation_dataframe(
        frame,
        evaluation_timeframe=Timeframe("1m"),
        column_keys=("close",),
    )
    assert frame.timestamps is timestamps_before
    assert frame.columns is columns_before
    assert frame.columns["close"] is close_before
    assert frame.columns["close"] == close


def test_available_at_preserves_microseconds() -> None:
    observed = datetime(2024, 6, 3, 14, 30, 0, 123456, tzinfo=UTC)
    frame = _frame(timestamps=(observed,), columns={"close": (1.0,)})
    timeframe = Timeframe("1m")
    table = build_evaluation_dataframe(
        frame,
        evaluation_timeframe=timeframe,
        column_keys=("close",),
    )
    expected_start, expected_available = derive_bar_interval(observed, timeframe)
    assert expected_available.microsecond == 123456
    assert table["timestamp"].to_list() == [expected_start]
    assert table["available_at"].to_list() == [expected_available]


def test_naive_timestamps_are_rejected() -> None:
    frame = _frame(
        timestamps=(datetime(2024, 6, 3, 14, 30),),
        columns={"close": (1.0,)},
    )
    with pytest.raises(ValidationError, match="timestamp must be timezone-aware"):
        build_evaluation_dataframe(
            frame,
            evaluation_timeframe=Timeframe("1m"),
            column_keys=("close",),
        )


def test_offset_timestamps_convert_to_utc_like_derive_bar_interval() -> None:
    offset = timezone(timedelta(hours=2))
    observed = datetime(2024, 6, 3, 16, 30, tzinfo=offset)
    frame = _frame(timestamps=(observed,), columns={"close": (1.0,)})
    timeframe = Timeframe("1m")
    table = build_evaluation_dataframe(
        frame,
        evaluation_timeframe=timeframe,
        column_keys=("close",),
    )
    expected_start, expected_available = derive_bar_interval(observed, timeframe)
    assert table["timestamp"].to_list() == [expected_start]
    assert table["available_at"].to_list() == [expected_available]
    assert getattr(table["timestamp"].dtype, "time_zone", None) == "UTC"
    assert getattr(table["available_at"].dtype, "time_zone", None) == "UTC"
