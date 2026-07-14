"""PyArrow table merge helpers for contract trade partitions."""

from __future__ import annotations

from decimal import Decimal

import pyarrow as pa

from trading_framework.infrastructure.storage.parquet.contract_trade_writer import (
    MARKET_TRADE_CONTRACT_PARQUET_SCHEMA,
    MARKET_TRADE_CONTRACT_PARQUET_SCHEMA_V1,
)
from trading_framework.market.contracts.storage_codec import (
    MISSING_TS_RECV_NS,
    price_nanos_from_decimal,
)


def ensure_v2_contract_trade_table(table: pa.Table) -> pa.Table:
    """Normalize contract trade tables to the v2 storage schema."""
    if table.schema.equals(MARKET_TRADE_CONTRACT_PARQUET_SCHEMA):
        return table.cast(MARKET_TRADE_CONTRACT_PARQUET_SCHEMA)
    if table.schema.equals(MARKET_TRADE_CONTRACT_PARQUET_SCHEMA_V1):
        return _upgrade_legacy_contract_trade_table(table)
    upgraded = table
    if "actual_contract" in upgraded.column_names and "contract_code" not in upgraded.column_names:
        upgraded = upgraded.rename_columns(
            [
                "contract_code" if name == "actual_contract" else name
                for name in upgraded.column_names
            ]
        )
    return upgraded.cast(MARKET_TRADE_CONTRACT_PARQUET_SCHEMA, safe=False)


def merge_contract_trade_tables(existing: pa.Table, new: pa.Table) -> pa.Table:
    """Concatenate and sort contract trade tables without domain deserialization."""
    if existing.num_rows == 0:
        return sort_contract_trade_table(ensure_v2_contract_trade_table(new))
    if new.num_rows == 0:
        return sort_contract_trade_table(ensure_v2_contract_trade_table(existing))
    merged = pa.concat_tables(
        [
            ensure_v2_contract_trade_table(existing),
            ensure_v2_contract_trade_table(new),
        ]
    )
    return sort_contract_trade_table(merged)


def sort_contract_trade_table(table: pa.Table) -> pa.Table:
    """Sort contract trades by event time and sequence."""
    normalized = ensure_v2_contract_trade_table(table)
    if normalized.num_rows <= 1:
        return normalized
    return normalized.sort_by(
        [
            ("ts_event_ns", "ascending"),
            ("sequence", "ascending"),
        ]
    )


def _upgrade_legacy_contract_trade_table(table: pa.Table) -> pa.Table:
    """Upgrade legacy v1 contract trade parquet to v2 without domain records."""
    normalized = table.cast(MARKET_TRADE_CONTRACT_PARQUET_SCHEMA_V1)
    rows = normalized.to_pylist()
    columns: dict[str, list[object]] = {
        "ts_event_ns": [],
        "ts_recv_ns": [],
        "price_nanos": [],
        "size": [],
        "instrument_id": [],
        "sequence": [],
        "publisher_id": [],
        "side": [],
        "product": [],
        "contract_code": [],
        "session_date": [],
        "source_file": [],
    }
    for row in rows:
        event_at = row["event_at"]
        received_at = row.get("received_at")
        sequence_raw = row.get("sequence")
        event_seconds = int(event_at.timestamp())
        event_micros = event_at.microsecond
        columns["ts_event_ns"].append(event_seconds * 1_000_000_000 + event_micros * 1_000)
        if received_at is None:
            columns["ts_recv_ns"].append(MISSING_TS_RECV_NS)
        else:
            recv_seconds = int(received_at.timestamp())
            recv_micros = received_at.microsecond
            columns["ts_recv_ns"].append(recv_seconds * 1_000_000_000 + recv_micros * 1_000)
        columns["price_nanos"].append(price_nanos_from_decimal(Decimal(str(row["price"]))))
        columns["size"].append(int(row["size"]))
        columns["instrument_id"].append(0)
        columns["sequence"].append(int(sequence_raw) if sequence_raw is not None else 0)
        columns["publisher_id"].append(0)
        columns["side"].append(row.get("side"))
        columns["product"].append(str(row["product"]))
        columns["contract_code"].append(str(row["actual_contract"]))
        columns["session_date"].append(row["session_date"])
        columns["source_file"].append(str(row["source_file"]))
    return pa.table(columns, schema=MARKET_TRADE_CONTRACT_PARQUET_SCHEMA)
