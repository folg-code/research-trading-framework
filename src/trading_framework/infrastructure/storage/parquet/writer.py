"""Parquet writer for MarketBar batches."""

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from trading_framework.core.profiling import optional_phase
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
    row_count = normalized.num_rows
    if row_count == 0:
        return []

    opens = normalized.column("open").to_pylist()
    highs = normalized.column("high").to_pylist()
    lows = normalized.column("low").to_pylist()
    closes = normalized.column("close").to_pylist()
    volumes = normalized.column("volume").to_pylist()
    observed_ats = normalized.column("observed_at").to_pylist()
    available_ats = normalized.column("available_at").to_pylist()

    return [
        MarketBar(
            open=Price(Decimal(str(opens[index]))),
            high=Price(Decimal(str(highs[index]))),
            low=Price(Decimal(str(lows[index]))),
            close=Price(Decimal(str(closes[index]))),
            volume=Volume(int(volumes[index])),
            observed_at=observed_ats[index].replace(tzinfo=UTC),
            available_at=available_ats[index].replace(tzinfo=UTC),
        )
        for index in range(row_count)
    ]


def filter_table_by_observed_range(
    table: pa.Table,
    *,
    start_at: datetime,
    end_at: datetime,
) -> pa.Table:
    """Return rows whose ``observed_at`` lies in the closed UTC range."""
    normalized = table.cast(MARKET_BAR_PARQUET_SCHEMA)
    if normalized.num_rows == 0:
        return normalized
    start_scalar = pa.scalar(start_at.astimezone(UTC).replace(tzinfo=None), type=pa.timestamp("us"))
    end_scalar = pa.scalar(end_at.astimezone(UTC).replace(tzinfo=None), type=pa.timestamp("us"))
    observed = normalized.column("observed_at")
    mask = pc.and_(  # type: ignore[attr-defined]
        pc.greater_equal(observed, start_scalar),  # type: ignore[attr-defined]
        pc.less_equal(observed, end_scalar),  # type: ignore[attr-defined]
    )
    return normalized.filter(mask)


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
        with optional_phase("ohlcv.parquet.read_table"):
            table = self.read_table(path)
        with optional_phase("ohlcv.parquet.table_to_bars"):
            return market_bars_from_table(table)
