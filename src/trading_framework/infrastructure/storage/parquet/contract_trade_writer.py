"""Parquet writer for contract-layer MarketTrade storage records."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from trading_framework.core.types import Price, Volume
from trading_framework.market.contracts.trade_record import ContractTradeRecord
from trading_framework.market.models import MarketTrade, TradeSide

MARKET_TRADE_CONTRACT_PARQUET_SCHEMA = pa.schema(
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
        ("source_file", pa.string()),
    ]
)


def _record_to_columns(record: ContractTradeRecord) -> dict[str, object]:
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
        "source_file": record.source_file,
    }


def _column_from_records(records: Sequence[ContractTradeRecord], field: str) -> list[object]:
    return [_record_to_columns(record)[field] for record in records]


def contract_trade_records_to_table(records: Sequence[ContractTradeRecord]) -> pa.Table:
    """Convert contract trade records to the contract-layer Parquet schema."""
    if not records:
        return pa.table(
            {
                field.name: pa.array([], type=field.type)
                for field in MARKET_TRADE_CONTRACT_PARQUET_SCHEMA
            },
            schema=MARKET_TRADE_CONTRACT_PARQUET_SCHEMA,
        )
    return pa.table(
        {
            field.name: _column_from_records(records, field.name)
            for field in MARKET_TRADE_CONTRACT_PARQUET_SCHEMA
        },
        schema=MARKET_TRADE_CONTRACT_PARQUET_SCHEMA,
    )


def contract_trade_records_from_table(table: pa.Table) -> list[ContractTradeRecord]:
    """Materialize contract trade records from contract-layer Parquet."""
    normalized = table.cast(MARKET_TRADE_CONTRACT_PARQUET_SCHEMA)
    rows = normalized.to_pylist()
    records: list[ContractTradeRecord] = []
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
            ContractTradeRecord(
                trade=trade,
                actual_contract=str(row["actual_contract"]),
                product=str(row["product"]),
                session_date=session_date,
                source_file=str(row["source_file"]),
            )
        )
    return records


class ParquetContractTradeWriter:
    """Write contract-layer trade records to Parquet files."""

    def write(self, path: Path, records: Sequence[ContractTradeRecord]) -> None:
        """Persist contract trade records to ``path``."""
        path.parent.mkdir(parents=True, exist_ok=True)
        table = contract_trade_records_to_table(records)
        pq.write_table(table, path)  # type: ignore[no-untyped-call]

    def read(self, path: Path) -> list[ContractTradeRecord]:
        """Read contract trade records from ``path``."""
        table = pq.ParquetFile(path).read()  # type: ignore[no-untyped-call]
        return contract_trade_records_from_table(table)
