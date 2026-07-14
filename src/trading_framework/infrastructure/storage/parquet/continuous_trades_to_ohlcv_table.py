"""Aggregate continuous-layer trade Arrow tables into OHLCV bar tables."""

from __future__ import annotations

from datetime import UTC, datetime

import polars as pl
import pyarrow as pa

from trading_framework.infrastructure.storage.parquet.writer import (
    MARKET_BAR_PARQUET_SCHEMA,
)
from trading_framework.time.models.timeframe import Timeframe

_ONE_MINUTE = Timeframe("1m")


def _empty_bars_table() -> pa.Table:
    return pa.table(
        {field.name: pa.array([], type=field.type) for field in MARKET_BAR_PARQUET_SCHEMA},
        schema=MARKET_BAR_PARQUET_SCHEMA,
    )


def continuous_trades_table_to_ohlcv_table(
    trades_table: pa.Table,
    *,
    target_timeframe: Timeframe = _ONE_MINUTE,
) -> pa.Table:
    """Aggregate one session of continuous trades into left-labeled OHLCV bars."""
    if trades_table.num_rows == 0:
        return _empty_bars_table()
    if target_timeframe != _ONE_MINUTE:
        msg = "continuous trades OHLCV derivation supports 1m only in this builder"
        raise ValueError(msg)

    frame = pl.from_arrow(trades_table)
    if not isinstance(frame, pl.DataFrame) or frame.is_empty():
        return _empty_bars_table()

    working = (
        frame.sort(["event_at", "sequence"])
        .with_columns(
            pl.col("price").cast(pl.Float64, strict=False).alias("price_num"),
            pl.col("event_at").dt.replace_time_zone("UTC").alias("event_at"),
        )
        .filter(pl.col("price_num").is_not_null())
    )
    if working.is_empty():
        return _empty_bars_table()

    aggregated = (
        working.group_by_dynamic(
            "event_at",
            every=target_timeframe.value,
            closed="left",
            label="left",
        )
        .agg(
            pl.col("price_num").first().alias("open_num"),
            pl.col("price_num").max().alias("high_num"),
            pl.col("price_num").min().alias("low_num"),
            pl.col("price_num").last().alias("close_num"),
            pl.col("size").sum().alias("volume"),
        )
        .sort("event_at")
    )
    if aggregated.is_empty():
        return _empty_bars_table()

    seconds = target_timeframe.total_seconds
    bars = aggregated.select(
        pl.col("open_num").cast(pl.Utf8).alias("open"),
        pl.col("high_num").cast(pl.Utf8).alias("high"),
        pl.col("low_num").cast(pl.Utf8).alias("low"),
        pl.col("close_num").cast(pl.Utf8).alias("close"),
        pl.col("volume").cast(pl.Int64),
        pl.col("event_at").dt.replace_time_zone(None).alias("observed_at"),
        (pl.col("event_at").dt.replace_time_zone(None) + pl.duration(seconds=seconds)).alias(
            "available_at"
        ),
    )
    arrow_table = bars.to_arrow()
    column_names = [field.name for field in MARKET_BAR_PARQUET_SCHEMA]
    return arrow_table.select(column_names).cast(MARKET_BAR_PARQUET_SCHEMA, safe=False)


def ohlcv_table_time_bounds(
    table: pa.Table,
    *,
    fallback: datetime,
) -> tuple[datetime, datetime]:
    """Return min/max observed_at from one OHLCV table."""
    if table.num_rows == 0:
        return fallback, fallback
    frame = pl.from_arrow(table)
    if not isinstance(frame, pl.DataFrame) or frame.is_empty():
        return fallback, fallback
    min_value = frame["observed_at"].min()
    max_value = frame["observed_at"].max()
    if not isinstance(min_value, datetime) or not isinstance(max_value, datetime):
        return fallback, fallback
    return _as_utc(min_value), _as_utc(max_value)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
