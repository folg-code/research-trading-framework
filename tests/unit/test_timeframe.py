"""Timeframe value object tests."""

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.time.models.timeframe import Timeframe


@pytest.mark.parametrize(
    ("value", "expected_seconds"),
    [
        ("1m", 60),
        ("5m", 300),
        ("1h", 3600),
        ("1d", 86400),
    ],
)
def test_timeframe_total_seconds(value: str, expected_seconds: int) -> None:
    timeframe = Timeframe(value)
    assert timeframe.total_seconds == expected_seconds


def test_tick_timeframe_is_event_level() -> None:
    timeframe = Timeframe("tick")
    assert timeframe.is_event_level
    assert timeframe.value == "tick"


def test_tick_timeframe_has_no_bar_duration() -> None:
    with pytest.raises(ValidationError, match="event-level timeframe tick"):
        _ = Timeframe("tick").total_seconds


def test_timeframe_normalizes_case_and_whitespace() -> None:
    timeframe = Timeframe(" 1H ")
    assert timeframe.value == "1h"


def test_invalid_timeframe_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Timeframe("2w")
