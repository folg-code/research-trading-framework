"""Tests for EVENT_AT_AVAILABLE alignment."""

from __future__ import annotations

import math
import random
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.data.align import (
    _is_active_event,
    align_event_at_available,
    align_output_series,
)
from trading_framework.market_analysis.models.alignment import AlignmentPolicy
from trading_framework.market_analysis.models.result import OutputSeries


def _utc(y: int, m: int, d: int, hh: int, mm: int) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=UTC)


def _timestamps_to_ns(timestamps: tuple[datetime, ...]) -> np.ndarray:
    return np.fromiter(
        (int(timestamp.timestamp() * 1_000_000_000) for timestamp in timestamps),
        dtype=np.int64,
        count=len(timestamps),
    )


def _align_event_at_available_reference(
    *,
    values: tuple[float, ...],
    available_at: tuple[datetime, ...],
    evaluation_timestamps: tuple[datetime, ...],
    inactive_event_fill: float,
) -> tuple[float, ...]:
    evaluation_ns = _timestamps_to_ns(evaluation_timestamps)
    aligned = [inactive_event_fill] * len(evaluation_timestamps)
    for value, source_available_at in zip(values, available_at, strict=True):
        if not _is_active_event(float(value), inactive_event_fill):
            continue
        source_ns = int(source_available_at.timestamp() * 1_000_000_000)
        target_index = int(np.searchsorted(evaluation_ns, source_ns, side="left"))
        if target_index < len(evaluation_ns):
            aligned[target_index] = float(value)
    return tuple(aligned)


def _assert_aligned_equal(
    actual: tuple[float, ...],
    expected: tuple[float, ...],
) -> None:
    assert len(actual) == len(expected)
    for actual_value, expected_value in zip(actual, expected, strict=True):
        if math.isnan(expected_value):
            assert math.isnan(actual_value)
        else:
            assert actual_value == expected_value


def test_align_event_at_available_matches_searchsorted_reference() -> None:
    evaluation_timestamps = tuple(_utc(2024, 6, 3, 10, minute) for minute in range(0, 15))
    available_at = (
        _utc(2024, 6, 3, 10, 5),
        _utc(2024, 6, 3, 10, 10),
        _utc(2024, 6, 3, 10, 15),
    )
    values = (0.0, 1.0, 0.0)
    inactive_event_fill = 0.0
    aligned = align_event_at_available(
        values=values,
        available_at=available_at,
        evaluation_timestamps=evaluation_timestamps,
        inactive_event_fill=inactive_event_fill,
    )
    expected = _align_event_at_available_reference(
        values=values,
        available_at=available_at,
        evaluation_timestamps=evaluation_timestamps,
        inactive_event_fill=inactive_event_fill,
    )
    _assert_aligned_equal(aligned, expected)


def test_align_event_at_available_preserves_collision_semantics() -> None:
    evaluation_timestamps = tuple(_utc(2024, 6, 3, 10, minute) for minute in range(0, 5))
    available_at = (
        _utc(2024, 6, 3, 10, 1),
        _utc(2024, 6, 3, 10, 1),
        _utc(2024, 6, 3, 10, 1),
    )
    values = (1.0, 2.0, 3.0)
    aligned = align_event_at_available(
        values=values,
        available_at=available_at,
        evaluation_timestamps=evaluation_timestamps,
        inactive_event_fill=0.0,
    )
    assert aligned[1] == 3.0


def test_is_active_event_uses_explicit_inactive_fill_not_inference() -> None:
    assert not _is_active_event(0.0, 0.0)
    assert _is_active_event(1.0, 0.0)
    assert not _is_active_event(math.nan, math.nan)
    assert _is_active_event(0.0, math.nan)


def test_align_output_series_requires_inactive_event_fill_for_event_policy() -> None:
    evaluation_timestamps = (_utc(2024, 6, 3, 10, 0), _utc(2024, 6, 3, 10, 1))
    series = OutputSeries(
        values=(1.0, 0.0),
        available_at=evaluation_timestamps,
    )
    with pytest.raises(ValidationError, match="inactive_event_fill"):
        align_output_series(
            series,
            evaluation_timestamps=evaluation_timestamps,
            policy=AlignmentPolicy.EVENT_AT_AVAILABLE,
        )


@pytest.mark.parametrize("inactive_event_fill", [0.0, math.nan])
def test_align_event_at_available_parity_on_random_fixtures(
    inactive_event_fill: float,
) -> None:
    rng = random.Random(42)
    start = _utc(2024, 1, 1, 0, 0)
    evaluation_timestamps = tuple(start + timedelta(minutes=minute) for minute in range(120))
    event_count = 25
    available_at = tuple(start + timedelta(minutes=rng.randint(0, 119)) for _ in range(event_count))
    if math.isnan(inactive_event_fill):
        values = tuple(
            float(rng.randint(10, 99)) if rng.random() < 0.3 else math.nan
            for _ in range(event_count)
        )
    else:
        values = tuple(1.0 if rng.random() < 0.3 else 0.0 for _ in range(event_count))

    aligned = align_event_at_available(
        values=values,
        available_at=available_at,
        evaluation_timestamps=evaluation_timestamps,
        inactive_event_fill=inactive_event_fill,
    )
    expected = _align_event_at_available_reference(
        values=values,
        available_at=available_at,
        evaluation_timestamps=evaluation_timestamps,
        inactive_event_fill=inactive_event_fill,
    )
    _assert_aligned_equal(aligned, expected)
