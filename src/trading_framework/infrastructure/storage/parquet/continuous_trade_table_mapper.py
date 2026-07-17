"""Map contract-layer Arrow tables to continuous-layer Parquet tables."""

from __future__ import annotations

from datetime import date

import polars as pl
import pyarrow as pa

from trading_framework.infrastructure.storage.parquet.continuous_trade_writer import (
    MARKET_TRADE_CONTINUOUS_PARQUET_SCHEMA,
    empty_continuous_trade_table,
)
from trading_framework.market.continuous.identity import continuous_symbol_label
from trading_framework.market.continuous.materializer import is_roll_boundary_session
from trading_framework.market.continuous.schedule import RollSchedule, entry_for_session
from trading_framework.market.contracts.storage_codec import MISSING_TS_RECV_NS, PRICE_NANOS_SCALE


def _price_nanos_to_string_expr() -> pl.Expr:
    whole = pl.col("price_nanos") // PRICE_NANOS_SCALE
    fraction = pl.col("price_nanos") % PRICE_NANOS_SCALE
    fraction_text = fraction.cast(pl.Utf8).str.zfill(9).str.strip_chars_end("0")
    return (
        pl.when(fraction_text.str.len_chars() == 0)
        .then(whole.cast(pl.Utf8))
        .otherwise(whole.cast(pl.Utf8) + "." + fraction_text)
    )


def _ns_to_naive_utc_us(column: str) -> pl.Expr:
    """Convert UTC epoch nanoseconds to naive UTC microsecond timestamps."""
    return (pl.col(column) // 1_000).cast(pl.Datetime(time_unit="us"))


def contract_table_to_continuous_table(
    contract_table: pa.Table,
    *,
    schedule: RollSchedule,
    session_date: date,
    active_contract: str,
) -> pa.Table:
    """Transform one contract session table into continuous-layer Arrow columns."""
    if contract_table.num_rows == 0 or entry_for_session(schedule, session_date) is None:
        return empty_continuous_trade_table()

    entry = entry_for_session(schedule, session_date)
    assert entry is not None

    contract_frame = pl.from_arrow(contract_table)
    if not isinstance(contract_frame, pl.DataFrame):
        return empty_continuous_trade_table()

    filtered = contract_frame.filter(
        (pl.col("contract_code") == active_contract) & (pl.col("session_date") == session_date)
    ).sort("ts_event_ns")
    if filtered.is_empty():
        return empty_continuous_trade_table()

    continuous_symbol = continuous_symbol_label(schedule.product)
    roll_boundary = is_roll_boundary_session(schedule, session_date)
    continuous = filtered.select(
        _price_nanos_to_string_expr().alias("price"),
        pl.col("size"),
        _ns_to_naive_utc_us("ts_event_ns").alias("event_at"),
        pl.col("side").fill_null("unknown").alias("side"),
        pl.when(pl.col("ts_recv_ns") == MISSING_TS_RECV_NS)
        .then(None)
        .otherwise(_ns_to_naive_utc_us("ts_recv_ns"))
        .alias("received_at"),
        pl.lit(None, dtype=pl.Utf8).alias("trade_id"),
        pl.when(pl.col("sequence") < 0).then(None).otherwise(pl.col("sequence")).alias("sequence"),
        pl.col("contract_code").alias("actual_contract"),
        pl.col("product"),
        pl.col("session_date"),
        pl.lit(continuous_symbol).alias("continuous_symbol"),
        pl.lit(entry.roll_id).alias("roll_id"),
        pl.lit(roll_boundary).alias("is_roll_boundary"),
    )
    arrow_table = continuous.to_arrow()
    if arrow_table.schema.equals(MARKET_TRADE_CONTINUOUS_PARQUET_SCHEMA):
        return arrow_table
    return arrow_table.cast(MARKET_TRADE_CONTINUOUS_PARQUET_SCHEMA, safe=False)
