"""OHLCV normalization contract tests."""

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_framework.market.normalization import (
    NormalizedBarRow,
    OhlcvColumnMapping,
    OhlcvImportConfig,
    OhlcvNormalizer,
)
from trading_framework.market.temporal import BarTimestampSemantics
from trading_framework.time.models.timeframe import Timeframe


class _StubOhlcvNormalizer:
    def normalize_row(
        self,
        raw_row: Mapping[str, str],
        config: OhlcvImportConfig,
    ) -> NormalizedBarRow:
        observed_at = datetime.fromisoformat(raw_row[config.column_mapping.timestamp])
        available_at = observed_at + timedelta(seconds=config.timeframe.total_seconds)
        return NormalizedBarRow(
            open=Decimal(raw_row[config.column_mapping.open]),
            high=Decimal(raw_row[config.column_mapping.high]),
            low=Decimal(raw_row[config.column_mapping.low]),
            close=Decimal(raw_row[config.column_mapping.close]),
            volume=int(raw_row[config.column_mapping.volume]),
            observed_at=observed_at,
            available_at=available_at,
        )


def test_ohlcv_import_config_stores_mapping() -> None:
    config = OhlcvImportConfig(
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
    )
    assert config.column_mapping.timestamp == "time"


def test_ohlcv_normalizer_protocol_is_implementable() -> None:
    normalizer: OhlcvNormalizer = _StubOhlcvNormalizer()
    row = normalizer.normalize_row(
        {
            "time": "2024-01-01T12:00:00+00:00",
            "open": "100",
            "high": "105",
            "low": "99",
            "close": "103",
            "volume": "1000",
        },
        OhlcvImportConfig(
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
            source_timezone=UTC,
        ),
    )
    assert row.close == Decimal("103")
