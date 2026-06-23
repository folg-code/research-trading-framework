"""CSV OHLCV importer tests."""

from datetime import UTC
from decimal import Decimal
from pathlib import Path

from trading_framework.infrastructure.importers.csv import CsvOhlcvImporter
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


def test_csv_ohlcv_importer_streams_fixture_rows(market_data_fixtures_dir: Path) -> None:
    fixture = market_data_fixtures_dir / "sample_ohlcv.csv"
    rows = list(CsvOhlcvImporter().iter_rows(fixture, _CONFIG))

    assert len(rows) == 2
    assert rows[0].close == Decimal("103")
    assert rows[1].volume == 1100


def test_csv_ohlcv_importer_integrates_inspector_and_normalizer(
    market_data_fixtures_dir: Path,
) -> None:
    fixture = market_data_fixtures_dir / "sample_ohlcv.csv"
    rows = list(CsvOhlcvImporter().iter_rows(fixture, _CONFIG))

    assert rows[0].observed_at.tzinfo is not None
    assert rows[0].available_at > rows[0].observed_at
