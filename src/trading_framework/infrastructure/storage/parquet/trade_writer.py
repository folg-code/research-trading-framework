"""Parquet writer for MarketTrade batches."""

from collections.abc import Sequence
from datetime import UTC
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketTrade, TradeSide

MARKET_TRADE_PARQUET_SCHEMA = pa.schema(
    [
        ("price", pa.string()),
        ("size", pa.int64()),
        ("event_at", pa.timestamp("us")),
        ("side", pa.string()),
        ("received_at", pa.timestamp("us")),
        ("trade_id", pa.string()),
        ("sequence", pa.int64()),
    ]
)


def _trade_to_columns(trade: MarketTrade) -> dict[str, object]:
    return {
        "price": str(trade.price.value),
        "size": trade.size.value,
        "event_at": trade.event_at.astimezone(UTC).replace(tzinfo=None),
        "side": trade.side.value,
        "received_at": (
            trade.received_at.astimezone(UTC).replace(tzinfo=None)
            if trade.received_at is not None
            else None
        ),
        "trade_id": trade.trade_id,
        "sequence": trade.sequence,
    }


def _column_from_trades(trades: Sequence[MarketTrade], field: str) -> list[object]:
    return [_trade_to_columns(trade)[field] for trade in trades]


def market_trades_to_table(trades: Sequence[MarketTrade]) -> pa.Table:
    """Convert market trades to a Parquet table with the canonical schema."""
    if not trades:
        return pa.table(
            {field.name: pa.array([], type=field.type) for field in MARKET_TRADE_PARQUET_SCHEMA},
            schema=MARKET_TRADE_PARQUET_SCHEMA,
        )
    return pa.table(
        {
            field.name: _column_from_trades(trades, field.name)
            for field in MARKET_TRADE_PARQUET_SCHEMA
        },
        schema=MARKET_TRADE_PARQUET_SCHEMA,
    )


def market_trades_from_table(table: pa.Table) -> list[MarketTrade]:
    """Materialize market trades from a canonical Parquet table."""
    normalized = table.cast(MARKET_TRADE_PARQUET_SCHEMA)
    rows = normalized.to_pylist()
    return [
        MarketTrade(
            price=Price(Decimal(str(row["price"]))),
            size=Volume(int(row["size"])),
            event_at=row["event_at"].replace(tzinfo=UTC),
            side=TradeSide(str(row["side"])),
            received_at=(
                row["received_at"].replace(tzinfo=UTC) if row["received_at"] is not None else None
            ),
            trade_id=row["trade_id"],
            sequence=row["sequence"],
        )
        for row in rows
    ]


class ParquetTradeWriter:
    """Write canonical market trades to Parquet files."""

    def write(self, path: Path, trades: Sequence[MarketTrade]) -> None:
        """Persist trades to ``path`` using the canonical market trade schema."""
        path.parent.mkdir(parents=True, exist_ok=True)
        table = market_trades_to_table(trades)
        pq.write_table(table, path)  # type: ignore[no-untyped-call]

    def read(self, path: Path) -> list[MarketTrade]:
        """Read trades written with the canonical market trade schema."""
        table = pq.ParquetFile(path).read()  # type: ignore[no-untyped-call]
        return market_trades_from_table(table)
