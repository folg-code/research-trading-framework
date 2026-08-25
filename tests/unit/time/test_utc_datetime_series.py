"""Unit tests for UTC datetime tuple ingest into Polars Series."""

from datetime import UTC, datetime, timedelta, timezone, tzinfo

import polars as pl
import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.time.utc_datetime_series import utc_datetime_series


class _UnspecifiedOffsetTz(tzinfo):
    def utcoffset(self, dt: datetime | None) -> timedelta | None:
        return None

    def dst(self, dt: datetime | None) -> timedelta | None:
        return None

    def tzname(self, dt: datetime | None) -> str | None:
        return "UNSPECIFIED"


def test_utc_1m_fixture_series_matches_input_instants() -> None:
    timestamps = tuple(
        datetime(2024, 6, 3, 14, 30, tzinfo=UTC) + timedelta(minutes=index) for index in range(3)
    )
    series = utc_datetime_series(timestamps)
    assert series.name == "timestamp"
    assert series.dtype == pl.Datetime("us", "UTC")
    assert series.to_list() == list(timestamps)


def test_naive_timestamps_are_rejected() -> None:
    with pytest.raises(ValidationError, match="timestamp must be timezone-aware"):
        utc_datetime_series((datetime(2024, 6, 3, 14, 30),))


def test_tzinfo_without_utcoffset_is_rejected() -> None:
    observed = datetime(2024, 6, 3, 14, 30, tzinfo=_UnspecifiedOffsetTz())
    with pytest.raises(ValidationError, match="timestamp must be timezone-aware"):
        utc_datetime_series((observed,))


def test_offset_aware_timestamps_convert_to_utc() -> None:
    offset = timezone(timedelta(hours=2))
    observed = datetime(2024, 6, 3, 16, 30, tzinfo=offset)
    series = utc_datetime_series((observed,))
    assert series.dtype == pl.Datetime("us", "UTC")
    assert series.to_list() == [observed.astimezone(UTC)]


def test_microseconds_are_preserved() -> None:
    observed = datetime(2024, 6, 3, 14, 30, 0, 123456, tzinfo=UTC)
    series = utc_datetime_series((observed,))
    assert series.to_list() == [observed]
    assert series.to_list()[0].microsecond == 123456


def test_empty_tuple_yields_empty_utc_datetime_series() -> None:
    series = utc_datetime_series(())
    assert series.name == "timestamp"
    assert series.dtype == pl.Datetime("us", "UTC")
    assert series.len() == 0
    assert series.to_list() == []
