"""Tests for CmeEsRthSessionResolver."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import polars as pl
import pytest

from trading_framework.time.sessions import (
    ES_RTH_SESSION_ID,
    OUTSIDE_RTH_SESSION_ID,
    CmeEsRthSessionResolver,
)

NEW_YORK = ZoneInfo("America/New_York")


def _utc(y: int, m: int, d: int, hh: int, mm: int) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=UTC)


@pytest.mark.parametrize(
    ("timestamp", "expect_rth", "expect_session"),
    [
        (_utc(2024, 6, 3, 13, 30), True, ES_RTH_SESSION_ID),
        (_utc(2024, 6, 3, 13, 29), False, OUTSIDE_RTH_SESSION_ID),
        (_utc(2024, 6, 3, 19, 59), True, ES_RTH_SESSION_ID),
        (_utc(2024, 6, 3, 20, 0), False, OUTSIDE_RTH_SESSION_ID),
        (_utc(2024, 1, 8, 14, 30), True, ES_RTH_SESSION_ID),
        (_utc(2024, 3, 11, 13, 30), True, ES_RTH_SESSION_ID),
        (_utc(2024, 6, 8, 15, 0), False, OUTSIDE_RTH_SESSION_ID),
    ],
)
def test_cme_es_rth_boundary_fixtures(
    timestamp: datetime,
    expect_rth: bool,
    expect_session: str,
) -> None:
    resolver = CmeEsRthSessionResolver()
    row = resolver.resolve(pl.Series("timestamp", [timestamp])).row(0, named=True)
    assert bool(row["is_rth"]) is expect_rth
    assert row["session_id"] == expect_session
    assert row["trading_day"] == timestamp.astimezone(NEW_YORK).date()


def test_holiday_mask_excludes_rth_on_weekday() -> None:
    holiday = date(2024, 6, 3)
    resolver = CmeEsRthSessionResolver(holiday_dates=frozenset({holiday}))
    row = resolver.resolve(pl.Series("timestamp", [_utc(2024, 6, 3, 13, 30)])).row(0, named=True)
    assert row["trading_day"] == holiday
    assert bool(row["is_rth"]) is False
    assert row["session_id"] == OUTSIDE_RTH_SESSION_ID


def test_batch_output_columns_and_length() -> None:
    timestamps = pl.Series(
        "timestamp",
        [_utc(2024, 6, 3, 13, 29), _utc(2024, 6, 3, 13, 30)],
    )
    frame = CmeEsRthSessionResolver().resolve(timestamps)
    assert frame.columns == ["timestamp", "trading_day", "session_id", "is_rth"]
    assert frame.height == 2
