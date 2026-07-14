"""Convert canonical OHLCV Parquet tables to columnar research batches."""

from __future__ import annotations

from datetime import UTC

import pyarrow as pa
import pyarrow.compute as pc

from trading_framework.infrastructure.storage.parquet.writer import MARKET_BAR_PARQUET_SCHEMA
from trading_framework.market_analysis.data.columnar import OhlcvColumnBatch


def ohlcv_column_batch_from_table(table: pa.Table) -> OhlcvColumnBatch:
    """Materialize one sorted column batch without per-bar ``MarketBar`` objects."""
    normalized = table.cast(MARKET_BAR_PARQUET_SCHEMA)
    if normalized.num_rows == 0:
        return OhlcvColumnBatch(
            timestamps=(),
            available_at=(),
            open=(),
            high=(),
            low=(),
            close=(),
            volume=(),
        )

    observed_ats = normalized.column("observed_at").to_pylist()
    available_ats = normalized.column("available_at").to_pylist()
    timestamps = tuple(observed.replace(tzinfo=UTC) for observed in observed_ats)
    available_at = tuple(observed.replace(tzinfo=UTC) for observed in available_ats)
    open_prices = _float_column(normalized, "open")
    high_prices = _float_column(normalized, "high")
    low_prices = _float_column(normalized, "low")
    close_prices = _float_column(normalized, "close")
    volume = tuple(float(value) for value in normalized.column("volume").to_pylist())
    return OhlcvColumnBatch(
        timestamps=timestamps,
        available_at=available_at,
        open=open_prices,
        high=high_prices,
        low=low_prices,
        close=close_prices,
        volume=volume,
    )


def sort_table_by_observed_at(table: pa.Table) -> pa.Table:
    """Return one OHLCV table sorted by ``observed_at`` ascending."""
    normalized = table.cast(MARKET_BAR_PARQUET_SCHEMA)
    if normalized.num_rows <= 1:
        return normalized
    indices = pc.sort_indices(normalized.column("observed_at"))  # type: ignore[attr-defined]
    return pc.take(normalized, indices)  # type: ignore[no-untyped-call]


def _float_column(table: pa.Table, field: str) -> tuple[float, ...]:
    values = pc.cast(table.column(field), pa.float64())  # type: ignore[no-untyped-call]
    return tuple(float(value) for value in values.to_pylist())
