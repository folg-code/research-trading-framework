"""UTC OHLCV normalizer tests."""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.normalization import UtcOhlcvNormalizer
from trading_framework.market.normalization import (
    NormalizedBarRow,
    OhlcvColumnMapping,
    OhlcvImportConfig,
    OhlcvNormalizer,
)
from trading_framework.market.temporal import BarTimestampSemantics
from trading_framework.time.models.timeframe import Timeframe

_CONFIG = OhlcvImportConfig(
    column_mapping=OhlcvColumnMapping(
        timestamp="time",
        open="open",
        high="high",
        low="low",
        close="close",
        volume="volume",
    ),
    timeframe=Timeframe("1m"),
    timestamp_semantics=BarTimestampSemantics.INTERVAL_START,
    source_timezone=timezone(timedelta(hours=-5)),
)

_RAW_ROW = {
    "time": "2024-01-01T07:00:00",
    "open": "100",
    "high": "105",
    "low": "99",
    "close": "103",
    "volume": "1000",
}


def test_utc_ohlcv_normalizer_converts_naive_timestamp_with_source_timezone() -> None:
    normalizer = UtcOhlcvNormalizer()
    row = normalizer.normalize_row(_RAW_ROW, _CONFIG)

    assert row.close == Decimal("103")
    assert row.volume == 1000
    assert row.observed_at == datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    assert row.available_at == row.observed_at + timedelta(minutes=1)


def test_utc_ohlcv_normalizer_applies_interval_end_semantics() -> None:
    config = OhlcvImportConfig(
        column_mapping=_CONFIG.column_mapping,
        timeframe=Timeframe("5m"),
        timestamp_semantics=BarTimestampSemantics.INTERVAL_END,
        source_timezone=UTC,
    )
    row = UtcOhlcvNormalizer().normalize_row(
        {
            **_RAW_ROW,
            "time": "2024-01-01T12:05:00+00:00",
        },
        config,
    )
    assert row.observed_at == datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    assert row.available_at == datetime(2024, 1, 1, 12, 5, tzinfo=UTC)


def test_utc_ohlcv_normalizer_rejects_naive_timestamp_without_source_timezone() -> None:
    config = OhlcvImportConfig(
        column_mapping=_CONFIG.column_mapping,
        timeframe=Timeframe("1m"),
        timestamp_semantics=BarTimestampSemantics.INTERVAL_START,
        source_timezone=None,
    )
    with pytest.raises(ValidationError, match="source_tz"):
        UtcOhlcvNormalizer().normalize_row(_RAW_ROW, config)


def test_utc_ohlcv_normalizer_rejects_negative_volume() -> None:
    with pytest.raises(ValidationError, match="non-negative"):
        UtcOhlcvNormalizer().normalize_row({**_RAW_ROW, "volume": "-1"}, _CONFIG)


def test_utc_ohlcv_normalizer_satisfies_protocol() -> None:
    normalizer: OhlcvNormalizer = UtcOhlcvNormalizer()
    row: NormalizedBarRow = normalizer.normalize_row(
        {
            "time": "2024-01-01T12:00:00+00:00",
            "open": "1",
            "high": "2",
            "low": "1",
            "close": "2",
            "volume": "10",
        },
        OhlcvImportConfig(
            column_mapping=_CONFIG.column_mapping,
            timeframe=Timeframe("1m"),
            timestamp_semantics=BarTimestampSemantics.INTERVAL_START,
            source_timezone=UTC,
        ),
    )
    assert row.observed_at.tzinfo == UTC
