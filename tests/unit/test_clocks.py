"""Clock implementation tests."""

from datetime import UTC, datetime

from trading_framework.time.clocks import FixedClock, SystemClock


def test_fixed_clock_returns_configured_time() -> None:
    fixed_time = datetime(2024, 1, 1, tzinfo=UTC)
    clock = FixedClock(fixed_time)
    assert clock.now() == fixed_time


def test_system_clock_returns_utc_aware_datetime() -> None:
    clock = SystemClock()
    now = clock.now()
    assert now.tzinfo is not None
    assert now.tzinfo.utcoffset(now) is not None
