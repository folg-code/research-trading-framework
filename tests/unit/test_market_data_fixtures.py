"""Market data fixture validation tests."""

from datetime import UTC
from pathlib import Path

from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.importers.csv import CsvOhlcvImporter
from trading_framework.infrastructure.validation import OhlcvBarValidator
from trading_framework.market.models import MarketBar
from trading_framework.market.normalization import OhlcvColumnMapping, OhlcvImportConfig
from trading_framework.market.temporal import BarTimestampSemantics
from trading_framework.time.models.timeframe import Timeframe

_CONFIG = OhlcvImportConfig(
    column_mapping=OhlcvColumnMapping(
        timestamp="timestamp",
        open="open",
        high="high",
        low="low",
        close="close",
        volume="volume",
    ),
    timeframe=Timeframe("1m"),
    timestamp_semantics=BarTimestampSemantics.INTERVAL_START,
    source_timezone=UTC,
)


def test_duplicate_timestamp_fixture_fails_batch_validation(
    market_data_fixtures_dir: Path,
) -> None:
    rows = list(
        CsvOhlcvImporter().iter_rows(
            market_data_fixtures_dir / "duplicate_timestamp_ohlcv.csv",
            _CONFIG,
        )
    )
    bars = [
        MarketBar(
            open=Price(row.open),
            high=Price(row.high),
            low=Price(row.low),
            close=Price(row.close),
            volume=Volume(row.volume),
            observed_at=row.observed_at,
            available_at=row.available_at,
        )
        for row in rows
    ]

    result = OhlcvBarValidator().validate(bars)

    assert result.is_valid is False
