"""Parquet writer for continuous-layer MarketTrade storage records."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from trading_framework.core.types import Price, Volume
from trading_framework.market.continuous.trade_record import ContinuousTradeRecord
from trading_framework.market.models import MarketTrade, TradeSide

MARKET_TRADE_CONTINUOUS_PARQUET_SCHEMA = pa.schema(
    [
        ("price", pa.string()),
        ("size", pa.int64()),
        ("event_at", pa.timestamp("us")),
        ("side", pa.string()),
        ("received_at", pa.timestamp("us")),
        ("trade_id", pa.string()),
        ("sequence", pa.int64()),
        ("actual_contract", pa.string()),
        ("product", pa.string()),
        ("session_date", pa.date32()),
        ("continuous_symbol", pa.string()),
        ("roll_id", pa.string()),
        ("is_roll_boundary", pa.bool_()),
    ]
)


def _record_to_columns(record: ContinuousTradeRecord) -> dict[str, object]:
    trade = record.trade
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
        "actual_contract": record.actual_contract,
        "product": record.product,
        "session_date": record.session_date,
        "continuous_symbol": record.continuous_symbol,
        "roll_id": record.roll_id,
        "is_roll_boundary": record.is_roll_boundary,
    }


def _column_from_records(records: Sequence[ContinuousTradeRecord], field: str) -> list[object]:
    return [_record_to_columns(record)[field] for record in records]


def continuous_trade_records_to_table(records: Sequence[ContinuousTradeRecord]) -> pa.Table:
    """Convert continuous trade records to the continuous-layer Parquet schema."""
    if not records:
        return pa.table(
            {
                field.name: pa.array([], type=field.type)
                for field in MARKET_TRADE_CONTINUOUS_PARQUET_SCHEMA
            },
            schema=MARKET_TRADE_CONTINUOUS_PARQUET_SCHEMA,
        )
    return pa.table(
        {
            field.name: _column_from_records(records, field.name)
            for field in MARKET_TRADE_CONTINUOUS_PARQUET_SCHEMA
        },
        schema=MARKET_TRADE_CONTINUOUS_PARQUET_SCHEMA,
    )


def continuous_trade_records_from_table(table: pa.Table) -> list[ContinuousTradeRecord]:
    """Materialize continuous trade records from continuous-layer Parquet."""
    normalized = table.cast(MARKET_TRADE_CONTINUOUS_PARQUET_SCHEMA)
    rows = normalized.to_pylist()
    records: list[ContinuousTradeRecord] = []
    for row in rows:
        trade = MarketTrade(
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
        session_value = row["session_date"]
        session_date = (
            session_value
            if isinstance(session_value, date)
            else date.fromisoformat(str(session_value))
        )
        records.append(
            ContinuousTradeRecord(
                trade=trade,
                actual_contract=str(row["actual_contract"]),
                product=str(row["product"]),
                session_date=session_date,
                continuous_symbol=str(row["continuous_symbol"]),
                roll_id=str(row["roll_id"]),
                is_roll_boundary=bool(row["is_roll_boundary"]),
            )
        )
    return records


class ParquetContinuousTradeWriter:
    """Write continuous-layer trade records to Parquet files."""

    def write(self, path: Path, records: Sequence[ContinuousTradeRecord]) -> None:
        """Persist continuous trade records to ``path``."""
        path.parent.mkdir(parents=True, exist_ok=True)
        table = continuous_trade_records_to_table(records)
        pq.write_table(table, path)  # type: ignore[no-untyped-call]

    def read(self, path: Path) -> list[ContinuousTradeRecord]:
        """Read continuous trade records from ``path``."""
        table = pq.ParquetFile(path).read()  # type: ignore[no-untyped-call]
        return continuous_trade_records_from_table(table)
