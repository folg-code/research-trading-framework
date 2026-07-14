"""Nanosecond session date resolution tests."""

from datetime import UTC, date, datetime

from trading_framework.market.contracts import trade_session_date, trade_session_dates_from_ns
from trading_framework.market.contracts.storage_codec import utc_ns_from_datetime


def test_trade_session_dates_from_ns_matches_datetime_path() -> None:
    event_times = [
        datetime(2025, 7, 14, 14, 30, tzinfo=UTC),
        datetime(2025, 7, 14, 15, 0, tzinfo=UTC),
        datetime(2025, 7, 14, 22, 0, tzinfo=UTC),
    ]
    event_times_ns = [utc_ns_from_datetime(event_at) for event_at in event_times]
    batch = trade_session_dates_from_ns(event_times_ns)
    singles = [trade_session_date(event_at) for event_at in event_times]
    assert batch == singles
    assert batch[0] == date(2025, 7, 14)
