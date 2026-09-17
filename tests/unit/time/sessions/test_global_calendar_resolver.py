"""Tests for GlobalSessionCalendarResolver (ADR-MA-015)."""

from datetime import UTC, date, datetime

import polars as pl
import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.time.sessions import (
    OUTSIDE_RTH_SESSION_ID,
    SESSION_ASIA_COLUMN,
    SESSION_LONDON_COLUMN,
    SESSION_NEW_YORK_COLUMN,
    CmeEsRthSessionResolver,
    GlobalSessionCalendarResolver,
)


def _utc(y: int, m: int, d: int, hh: int, mm: int) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=UTC)


def test_output_columns_are_a_superset_of_cme_es_rth() -> None:
    timestamps = pl.Series("timestamp", [_utc(2024, 6, 3, 13, 30)])
    frame = GlobalSessionCalendarResolver().resolve(timestamps)
    assert set(frame.columns) == {
        "timestamp",
        "trading_day",
        "session_id",
        "is_rth",
        SESSION_ASIA_COLUMN,
        SESSION_LONDON_COLUMN,
        SESSION_NEW_YORK_COLUMN,
    }


def test_rth_columns_are_byte_identical_to_cme_es_rth_resolver() -> None:
    timestamps = pl.Series(
        "timestamp",
        [_utc(2024, 6, 3, 13, 29), _utc(2024, 6, 3, 13, 30), _utc(2024, 6, 3, 20, 0)],
    )
    rth_frame = CmeEsRthSessionResolver().resolve(timestamps)
    global_frame = GlobalSessionCalendarResolver().resolve(timestamps)
    assert global_frame["trading_day"].to_list() == rth_frame["trading_day"].to_list()
    assert global_frame["session_id"].to_list() == rth_frame["session_id"].to_list()
    assert global_frame["is_rth"].to_list() == rth_frame["is_rth"].to_list()


@pytest.mark.parametrize(
    ("timestamp", "expected"),
    [
        (_utc(2024, 6, 2, 15, 0), True),  # JST Mon 00:00 -- window start, inclusive
        (_utc(2024, 6, 2, 23, 59), True),  # JST Mon 08:59 -- inside
        (_utc(2024, 6, 3, 0, 0), False),  # JST Mon 09:00 -- window end, exclusive
        (_utc(2024, 6, 2, 14, 59), False),  # JST Sun 23:59 -- wrong weekday
    ],
)
def test_asia_session_boundaries(timestamp: datetime, expected: bool) -> None:
    row = (
        GlobalSessionCalendarResolver()
        .resolve(pl.Series("timestamp", [timestamp]))
        .row(0, named=True)
    )
    assert bool(row[SESSION_ASIA_COLUMN]) is expected


@pytest.mark.parametrize(
    ("timestamp", "expected"),
    [
        (_utc(2024, 1, 8, 8, 0), True),  # London (winter, GMT) 08:00 -- window start
        (_utc(2024, 1, 8, 7, 59), False),  # 07:59 -- before window
        (_utc(2024, 1, 8, 16, 29), True),  # 16:29 -- inside
        (_utc(2024, 1, 8, 16, 30), False),  # 16:30 -- window end, exclusive
    ],
)
def test_london_session_boundaries(timestamp: datetime, expected: bool) -> None:
    row = (
        GlobalSessionCalendarResolver()
        .resolve(pl.Series("timestamp", [timestamp]))
        .row(0, named=True)
    )
    assert bool(row[SESSION_LONDON_COLUMN]) is expected


@pytest.mark.parametrize(
    ("timestamp", "expected"),
    [
        (_utc(2024, 6, 3, 13, 30), True),  # NY 09:30 -- window start, same as CME ES RTH open
        (_utc(2024, 6, 3, 13, 29), False),
        (_utc(2024, 6, 3, 19, 59), True),  # NY 15:59 -- inside
        (_utc(2024, 6, 3, 20, 0), False),  # NY 16:00 -- window end, exclusive
    ],
)
def test_new_york_session_boundaries(timestamp: datetime, expected: bool) -> None:
    row = (
        GlobalSessionCalendarResolver()
        .resolve(pl.Series("timestamp", [timestamp]))
        .row(0, named=True)
    )
    assert bool(row[SESSION_NEW_YORK_COLUMN]) is expected


def test_new_york_session_and_is_rth_are_stored_separately() -> None:
    """Same hours today, but two different columns -- not one implying the other."""
    timestamps = pl.Series("timestamp", [_utc(2024, 6, 3, 13, 30)])
    frame = GlobalSessionCalendarResolver().resolve(timestamps)
    assert frame.columns.count("is_rth") == 1
    assert frame.columns.count(SESSION_NEW_YORK_COLUMN) == 1
    assert frame["is_rth"][0] == frame[SESSION_NEW_YORK_COLUMN][0] is True


def test_holiday_dates_still_mask_is_rth_but_not_named_sessions() -> None:
    """holiday_dates is an RTH-specific concept (ADR-MA-013); named sessions are unaffected."""
    holiday = date(2024, 6, 3)
    resolver = GlobalSessionCalendarResolver(holiday_dates=frozenset({holiday}))
    row = resolver.resolve(pl.Series("timestamp", [_utc(2024, 6, 3, 13, 30)])).row(0, named=True)
    assert bool(row["is_rth"]) is False
    assert row["session_id"] == OUTSIDE_RTH_SESSION_ID
    assert bool(row[SESSION_NEW_YORK_COLUMN]) is True


def test_resolver_rejects_empty_timestamps() -> None:
    empty = pl.Series("timestamp", [], dtype=pl.Datetime("us", "UTC"))
    with pytest.raises(ValidationError, match="non-empty"):
        GlobalSessionCalendarResolver().resolve(empty)


def test_batch_output_length_matches_input() -> None:
    timestamps = pl.Series(
        "timestamp",
        [_utc(2024, 6, 3, 13, 29), _utc(2024, 6, 3, 13, 30), _utc(2024, 1, 8, 8, 0)],
    )
    frame = GlobalSessionCalendarResolver().resolve(timestamps)
    assert frame.height == timestamps.len()
