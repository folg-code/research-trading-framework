"""UTC timestamp primitive tests."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.time.models.utc_instant import normalize_to_utc, require_utc_aware


def test_require_utc_aware_accepts_utc_datetime() -> None:
    value = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    assert require_utc_aware(value) == value


def test_require_utc_aware_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError):
        require_utc_aware(datetime(2024, 1, 1, 12, 0))


def test_normalize_to_utc_converts_aware_datetime() -> None:
    offset = timezone(timedelta(hours=2))
    local = datetime(2024, 6, 1, 12, 0, tzinfo=offset)
    normalized = normalize_to_utc(local)
    assert normalized.tzinfo == UTC
    assert normalized.hour == 10


def test_normalize_to_utc_requires_source_tz_for_naive_datetime() -> None:
    naive = datetime(2024, 6, 1, 12, 0)
    with pytest.raises(ValidationError):
        normalize_to_utc(naive)

    normalized = normalize_to_utc(naive, source_tz=UTC)
    assert normalized.tzinfo == UTC
