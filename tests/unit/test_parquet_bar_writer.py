"""Parquet bar writer tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq

from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.parquet.writer import (
    MARKET_BAR_PARQUET_SCHEMA,
    ParquetBarWriter,
)
from trading_framework.market.models import MarketBar


def _bar(minute: int) -> MarketBar:
    observed_at = datetime(2024, 1, 1, 12, minute, tzinfo=UTC)
    return MarketBar(
        open=Price(Decimal("100.5")),
        high=Price(Decimal("105.25")),
        low=Price(Decimal("99.75")),
        close=Price(Decimal("103.125")),
        volume=Volume(1000 + minute),
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
    )


def test_parquet_bar_writer_round_trips_bars(tmp_path: Path) -> None:
    path = tmp_path / "bars.parquet"
    bars = [_bar(0), _bar(1)]
    writer = ParquetBarWriter()

    writer.write(path, bars)
    loaded = writer.read(path)

    assert loaded == bars


def test_parquet_bar_writer_uses_stable_schema(tmp_path: Path) -> None:
    path = tmp_path / "bars.parquet"
    ParquetBarWriter().write(path, [_bar(0)])

    schema = pq.read_schema(path)  # type: ignore[no-untyped-call]
    assert schema.equals(MARKET_BAR_PARQUET_SCHEMA)
