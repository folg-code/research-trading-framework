"""Bar timestamp convention tests."""

from datetime import UTC, datetime, timedelta

from trading_framework.market.temporal import (
    BarTimestampSemantics,
    derive_bar_interval,
    normalize_provider_bar_timestamp,
)
from trading_framework.time.models.timeframe import Timeframe


def test_derive_bar_interval_uses_interval_start_and_timeframe() -> None:
    observed_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    available_at = derive_bar_interval(observed_at, Timeframe("1m"))[1]
    assert available_at == observed_at + timedelta(minutes=1)


def test_normalize_provider_bar_timestamp_from_interval_start() -> None:
    timestamp = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    observed_at, available_at = normalize_provider_bar_timestamp(
        timestamp,
        timeframe=Timeframe("5m"),
        semantics=BarTimestampSemantics.INTERVAL_START,
    )
    assert observed_at == timestamp
    assert available_at == timestamp + timedelta(minutes=5)


def test_normalize_provider_bar_timestamp_from_interval_end() -> None:
    interval_end = datetime(2024, 1, 1, 12, 5, tzinfo=UTC)
    observed_at, available_at = normalize_provider_bar_timestamp(
        interval_end,
        timeframe=Timeframe("5m"),
        semantics=BarTimestampSemantics.INTERVAL_END,
    )
    assert observed_at == datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    assert available_at == interval_end
