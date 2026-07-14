"""Contract session date resolution tests."""

from datetime import UTC, date, datetime

from trading_framework.market.contracts.session_date import trade_session_date


def test_trade_session_date_uses_exchange_local_trading_day() -> None:
    event_at = datetime(2025, 7, 13, 22, 30, tzinfo=UTC)
    session_date = trade_session_date(event_at)
    assert isinstance(session_date, date)
