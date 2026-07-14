"""Parquet writer for MarketBar batches."""

from collections.abc import Sequence
from datetime import UTC
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketBar

MARKET_BAR_PARQUET_SCHEMA = pa.schema(
    [
        ("open", pa.string()),
        ("high", pa.string()),
        ("low", pa.string()),
        ("close", pa.string()),
        ("volume", pa.int64()),
        ("observed_at", pa.timestamp("us")),
        ("available_at", pa.timestamp("us")),
    ]
)


def _bar_to_columns(bar: MarketBar) -> dict[str, object]:
    return {
        "open": str(bar.open.value),
        "high": str(bar.high.value),
        "low": str(bar.low.value),
        "close": str(bar.close.value),
        "volume": bar.volume.value,
        "observed_at": bar.observed_at.astimezone(UTC).replace(tzinfo=None),
        "available_at": bar.available_at.astimezone(UTC).replace(tzinfo=None),
    }


def _column_from_bars(bars: Sequence[MarketBar], field: str) -> list[object]:
    return [_bar_to_columns(bar)[field] for bar in bars]


def market_bars_to_table(bars: Sequence[MarketBar]) -> pa.Table:
    """Convert market bars to a Parquet table with the canonical schema."""
    if not bars:
        return pa.table(
            {field.name: pa.array([], type=field.type) for field in MARKET_BAR_PARQUET_SCHEMA},
            schema=MARKET_BAR_PARQUET_SCHEMA,
        )
    return pa.table(
        {field.name: _column_from_bars(bars, field.name) for field in MARKET_BAR_PARQUET_SCHEMA},
        schema=MARKET_BAR_PARQUET_SCHEMA,
    )


def market_bars_from_table(table: pa.Table) -> list[MarketBar]:
    """Materialize market bars from a canonical Parquet table."""
    normalized = table.cast(MARKET_BAR_PARQUET_SCHEMA)
    rows = normalized.to_pylist()
    return [
        MarketBar(
            open=Price(Decimal(str(row["open"]))),
            high=Price(Decimal(str(row["high"]))),
            low=Price(Decimal(str(row["low"]))),
            close=Price(Decimal(str(row["close"]))),
            volume=Volume(int(row["volume"])),
            observed_at=row["observed_at"].replace(tzinfo=UTC),
            available_at=row["available_at"].replace(tzinfo=UTC),
        )
        for row in rows
    ]


class ParquetBarWriter:
    """Write canonical OHLCV bars to Parquet files."""

    def write_table(self, path: Path, table: pa.Table) -> None:
        """Persist one OHLCV table to ``path`` using the canonical schema."""
        path.parent.mkdir(parents=True, exist_ok=True)
        column_names = [field.name for field in MARKET_BAR_PARQUET_SCHEMA]
        normalized = table.select(column_names).cast(MARKET_BAR_PARQUET_SCHEMA, safe=False)
        pq.write_table(normalized, path)  # type: ignore[no-untyped-call]

    def read_table(self, path: Path) -> pa.Table:
        """Read OHLCV parquet without materializing domain bars."""
        table = pq.read_table(path)  # type: ignore[no-untyped-call]
        column_names = [field.name for field in MARKET_BAR_PARQUET_SCHEMA]
        return table.select(column_names).cast(MARKET_BAR_PARQUET_SCHEMA, safe=False)

    def write(self, path: Path, bars: Sequence[MarketBar]) -> None:
        """Persist bars to ``path`` using the canonical market bar schema."""
        self.write_table(path, market_bars_to_table(bars))

    def read(self, path: Path) -> list[MarketBar]:
        """Read bars written with the canonical market bar schema."""
        return market_bars_from_table(self.read_table(path))
