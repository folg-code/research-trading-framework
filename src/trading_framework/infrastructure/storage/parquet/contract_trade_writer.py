"""Parquet writer for contract-layer trade storage records."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pyarrow as pa
import pyarrow.parquet as pq

from trading_framework.infrastructure.importers.databento.contract_chunk_columns import (
    ContractChunkColumns,
)
from trading_framework.infrastructure.observability.profile_context import active_phase_timer
from trading_framework.market.contracts.trade_record import ContractTradeRecord

MARKET_TRADE_CONTRACT_PARQUET_SCHEMA = pa.schema(
    [
        ("ts_event_ns", pa.int64()),
        ("ts_recv_ns", pa.int64()),
        ("price_nanos", pa.int64()),
        ("size", pa.int64()),
        ("instrument_id", pa.int64()),
        ("sequence", pa.int64()),
        ("publisher_id", pa.int64()),
        ("side", pa.string()),
        ("product", pa.string()),
        ("contract_code", pa.string()),
        ("session_date", pa.date32()),
        ("source_file", pa.string()),
    ]
)


def empty_contract_trade_table() -> pa.Table:
    """Return an empty table using the contract trade Parquet schema."""
    return pa.table(
        {
            field.name: pa.array([], type=field.type)
            for field in MARKET_TRADE_CONTRACT_PARQUET_SCHEMA
        },
        schema=MARKET_TRADE_CONTRACT_PARQUET_SCHEMA,
    )


MARKET_TRADE_CONTRACT_PARQUET_SCHEMA_V1 = pa.schema(
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


def _build_storage_columns(records: Sequence[ContractTradeRecord]) -> dict[str, list[object]]:
    row_count = len(records)
    columns: dict[str, list[object]] = {
        "ts_event_ns": [0] * row_count,
        "ts_recv_ns": [0] * row_count,
        "price_nanos": [0] * row_count,
        "size": [0] * row_count,
        "instrument_id": [0] * row_count,
        "sequence": [0] * row_count,
        "publisher_id": [0] * row_count,
        "side": [None] * row_count,
        "product": [""] * row_count,
        "contract_code": [""] * row_count,
        "session_date": [date.today()] * row_count,
        "source_file": [""] * row_count,
    }
    for index, record in enumerate(records):
        columns["ts_event_ns"][index] = record.ts_event_ns
        columns["ts_recv_ns"][index] = record.ts_recv_ns
        columns["price_nanos"][index] = record.price_nanos
        columns["size"][index] = record.size
        columns["instrument_id"][index] = record.instrument_id
        columns["sequence"][index] = record.sequence
        columns["publisher_id"][index] = record.publisher_id
        columns["side"][index] = record.side
        columns["product"][index] = record.product
        columns["contract_code"][index] = record.contract_code
        columns["session_date"][index] = record.session_date
        columns["source_file"][index] = record.source_file
    return columns


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
    timer = active_phase_timer()
    if timer is not None:
        with timer.phase("parquet.build_columns"):
            columns = _build_storage_columns(records)
        with timer.phase("parquet.build_table"):
            return pa.table(columns, schema=MARKET_TRADE_CONTRACT_PARQUET_SCHEMA)
    return pa.table(_build_storage_columns(records), schema=MARKET_TRADE_CONTRACT_PARQUET_SCHEMA)


def contract_trade_columns_to_table(
    columns: ContractChunkColumns,
    *,
    product: str,
    contract_code: str,
    session_date: date,
    source_file: str,
) -> pa.Table:
    """Convert batch column buffers to the contract-layer Parquet schema."""
    row_count = len(columns)
    if row_count == 0:
        return pa.table(
            {
                field.name: pa.array([], type=field.type)
                for field in MARKET_TRADE_CONTRACT_PARQUET_SCHEMA
            },
            schema=MARKET_TRADE_CONTRACT_PARQUET_SCHEMA,
        )
    timer = active_phase_timer()
    table_columns: dict[str, object] = {
        "ts_event_ns": columns.ts_event_ns,
        "ts_recv_ns": columns.ts_recv_ns,
        "price_nanos": columns.price_nanos,
        "size": columns.size,
        "instrument_id": columns.instrument_id,
        "sequence": columns.sequence,
        "publisher_id": columns.publisher_id,
        "side": columns.side,
        "product": pa.array([product] * row_count, type=pa.string()),
        "contract_code": pa.array([contract_code] * row_count, type=pa.string()),
        "session_date": pa.array([session_date] * row_count, type=pa.date32()),
        "source_file": pa.array([source_file] * row_count, type=pa.string()),
    }
    if timer is not None:
        with timer.phase("parquet.build_table"):
            return pa.table(table_columns, schema=MARKET_TRADE_CONTRACT_PARQUET_SCHEMA)
    return pa.table(table_columns, schema=MARKET_TRADE_CONTRACT_PARQUET_SCHEMA)


def _record_from_storage_row(row: Mapping[str, Any]) -> ContractTradeRecord:
    session_value = row["session_date"]
    session_date = (
        session_value if isinstance(session_value, date) else date.fromisoformat(str(session_value))
    )
    side_value = row.get("side")
    return ContractTradeRecord(
        ts_event_ns=cast(int, row["ts_event_ns"]),
        ts_recv_ns=cast(int, row["ts_recv_ns"]),
        price_nanos=cast(int, row["price_nanos"]),
        size=cast(int, row["size"]),
        instrument_id=cast(int, row["instrument_id"]),
        sequence=cast(int, row["sequence"]),
        publisher_id=cast(int, row["publisher_id"]),
        side=None if side_value is None else str(side_value),
        product=str(row["product"]),
        contract_code=str(row["contract_code"]),
        session_date=session_date,
        source_file=str(row["source_file"]),
    )


def _record_from_legacy_row(row: dict[str, object]) -> ContractTradeRecord:
    from trading_framework.market.contracts.storage_codec import (
        MISSING_TS_RECV_NS,
        price_nanos_from_decimal,
        utc_ns_from_datetime,
    )

    event_at = row["event_at"]
    if not isinstance(event_at, datetime):
        msg = "legacy event_at must be datetime"
        raise TypeError(msg)
    received_raw = row.get("received_at")
    received_at = received_raw if isinstance(received_raw, datetime) else None
    sequence_raw = row.get("sequence")
    return ContractTradeRecord(
        ts_event_ns=utc_ns_from_datetime(event_at.replace(tzinfo=UTC)),
        ts_recv_ns=(
            MISSING_TS_RECV_NS
            if received_at is None
            else utc_ns_from_datetime(received_at.replace(tzinfo=UTC))
        ),
        price_nanos=price_nanos_from_decimal(Decimal(str(row["price"]))),
        size=cast(int, row["size"]),
        instrument_id=0,
        sequence=cast(int, sequence_raw) if sequence_raw is not None else 0,
        publisher_id=0,
        side=str(row["side"]) if row.get("side") is not None else None,
        product=str(row["product"]),
        contract_code=str(row["actual_contract"]),
        session_date=(
            row["session_date"]
            if isinstance(row["session_date"], date)
            else date.fromisoformat(str(row["session_date"]))
        ),
        source_file=str(row["source_file"]),
    )


def contract_trade_records_from_table(table: pa.Table) -> list[ContractTradeRecord]:
    """Materialize contract trade records from contract-layer Parquet."""
    if table.schema.equals(MARKET_TRADE_CONTRACT_PARQUET_SCHEMA):
        rows = table.cast(MARKET_TRADE_CONTRACT_PARQUET_SCHEMA).to_pylist()
        return [_record_from_storage_row(row) for row in rows]
    if table.schema.equals(MARKET_TRADE_CONTRACT_PARQUET_SCHEMA_V1):
        rows = table.cast(MARKET_TRADE_CONTRACT_PARQUET_SCHEMA_V1).to_pylist()
        return [_record_from_legacy_row(row) for row in rows]
    msg = f"unsupported contract trade parquet schema: {table.schema}"
    raise ValueError(msg)


class ParquetContractTradeWriter:
    """Write contract-layer trade records to Parquet files."""

    def write_table(self, path: Path, table: pa.Table) -> None:
        """Persist one contract trade table to ``path``."""
        timer = active_phase_timer()
        path.parent.mkdir(parents=True, exist_ok=True)
        normalized = table.cast(MARKET_TRADE_CONTRACT_PARQUET_SCHEMA, safe=False)
        if timer is not None:
            with timer.phase("parquet.write_file"):
                pq.write_table(normalized, path, use_dictionary=False)  # type: ignore[no-untyped-call]
            return
        pq.write_table(normalized, path, use_dictionary=False)  # type: ignore[no-untyped-call]

    def read_table(self, path: Path) -> pa.Table:
        """Read contract trade parquet without materializing domain records."""
        timer = active_phase_timer()
        if timer is not None:
            with timer.phase("parquet.read_file"):
                table = pq.ParquetFile(path).read()  # type: ignore[no-untyped-call]
            return table.cast(MARKET_TRADE_CONTRACT_PARQUET_SCHEMA, safe=False)
        table = pq.ParquetFile(path).read()  # type: ignore[no-untyped-call]
        return table.cast(MARKET_TRADE_CONTRACT_PARQUET_SCHEMA, safe=False)

    def write(self, path: Path, records: Sequence[ContractTradeRecord]) -> None:
        """Persist contract trade records to ``path``."""
        timer = active_phase_timer()
        path.parent.mkdir(parents=True, exist_ok=True)
        if timer is not None:
            with timer.phase("parquet.serialize_table"):
                table = contract_trade_records_to_table(records)
            with timer.phase("parquet.write_file"):
                pq.write_table(table, path, use_dictionary=False)  # type: ignore[no-untyped-call]
            return
        table = contract_trade_records_to_table(records)
        pq.write_table(table, path, use_dictionary=False)  # type: ignore[no-untyped-call]

    def read(self, path: Path) -> list[ContractTradeRecord]:
        """Read contract trade records from ``path``."""
        timer = active_phase_timer()
        if timer is not None:
            with timer.phase("parquet.read_file"):
                table = pq.ParquetFile(path).read()  # type: ignore[no-untyped-call]
            with timer.phase("parquet.deserialize_table"):
                return contract_trade_records_from_table(table)
        table = pq.ParquetFile(path).read()  # type: ignore[no-untyped-call]
        return contract_trade_records_from_table(table)
