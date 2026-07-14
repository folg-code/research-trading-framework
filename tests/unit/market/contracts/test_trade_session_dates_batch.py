"""Batch session date resolution tests."""

from datetime import UTC, date, datetime

from trading_framework.market.contracts import trade_session_date, trade_session_dates


def test_trade_session_dates_matches_single_trade_lookup() -> None:
    event_times = [
        datetime(2025, 7, 14, 14, 30, tzinfo=UTC),
        datetime(2025, 7, 14, 15, 0, tzinfo=UTC),
        datetime(2025, 7, 14, 22, 0, tzinfo=UTC),
    ]
    batch = trade_session_dates(event_times)
    singles = [trade_session_date(event_at) for event_at in event_times]
    assert batch == singles
    assert batch[0] == date(2025, 7, 14)
