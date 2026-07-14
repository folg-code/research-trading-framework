"""Normalize Databento trades rows to storage-ready scalar fields."""

from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict

import numpy as np
import numpy.typing as npt
import pandas as pd  # type: ignore[import-untyped]

from trading_framework.infrastructure.importers.databento.side import map_databento_trade_side
from trading_framework.market.contracts.storage_codec import (
    MISSING_TS_RECV_NS,
    price_nanos_from_decimal,
    utc_ns_from_datetime,
)
from trading_framework.market.models import TradeSide
from trading_framework.time.models.utc_instant import require_utc_aware


class DatabentoStorageTradeFields(TypedDict):
    """Storage-ready scalars decoded from one Databento trades row."""

    ts_event_ns: int
    ts_recv_ns: int
    price_nanos: int
    size: int
    instrument_id: int
    sequence: int
    publisher_id: int
    side: str | None


def databento_ts_to_ns(value: Any) -> int:
    """Normalize Databento timestamp values to UTC nanoseconds."""
    if isinstance(value, int):
        return value
    if isinstance(value, datetime):
        return utc_ns_from_datetime(require_utc_aware(value))
    msg = f"unsupported databento timestamp type: {type(value)!r}"
    raise TypeError(msg)


def databento_price_to_nanos(value: Any) -> int:
    """Normalize Databento fixed-point prices without float/string round-trips."""
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value * 1_000_000_000)
    from decimal import Decimal

    return price_nanos_from_decimal(Decimal(str(value)))


def databento_optional_int(value: Any, *, default: int = 0) -> int:
    """Normalize optional integer DBN fields."""
    if value is None:
        return default
    return int(value)


def map_databento_trades_row_to_storage(row: Any) -> DatabentoStorageTradeFields:
    """Map one Databento trades row to storage-ready scalar fields."""
    side = map_databento_trade_side(getattr(row, "side", None))
    received_raw = getattr(row, "ts_recv", None)
    return DatabentoStorageTradeFields(
        ts_event_ns=databento_ts_to_ns(row.ts_event),
        ts_recv_ns=(
            MISSING_TS_RECV_NS if received_raw is None else databento_ts_to_ns(received_raw)
        ),
        price_nanos=databento_price_to_nanos(row.price),
        size=int(row.size),
        instrument_id=databento_optional_int(getattr(row, "instrument_id", None)),
        sequence=databento_optional_int(getattr(row, "sequence", None)),
        publisher_id=databento_optional_int(getattr(row, "publisher_id", None)),
        side=side.value,
    )


def normalize_ts_series(series: pd.Series) -> npt.NDArray[np.int64]:
    """Normalize one Databento timestamp column to UTC nanoseconds."""
    if series.empty:
        return np.array([], dtype=np.int64)
    if pd.api.types.is_integer_dtype(series):
        return np.asarray(series.to_numpy(dtype=np.int64, na_value=0), dtype=np.int64)
    if pd.api.types.is_datetime64_any_dtype(series):
        normalized = series
        if getattr(series.dt, "tz", None) is None:
            normalized = series.dt.tz_localize("UTC")
        elif str(series.dt.tz) != "UTC":
            normalized = series.dt.tz_convert("UTC")
        return np.asarray(normalized.astype(np.int64).to_numpy(), dtype=np.int64)
    values = series.to_list()
    first = next(value for value in values if value is not None and not pd.isna(value))
    if isinstance(first, int):
        return np.array(
            [int(value) if value is not None and not pd.isna(value) else 0 for value in values],
            dtype=np.int64,
        )
    if isinstance(first, datetime):
        return np.array(
            [
                utc_ns_from_datetime(require_utc_aware(value))
                if value is not None and not pd.isna(value)
                else 0
                for value in values
            ],
            dtype=np.int64,
        )
    msg = f"unsupported databento timestamp dtype: {series.dtype!r}"
    raise TypeError(msg)


def normalize_ts_recv_series(series: pd.Series) -> npt.NDArray[np.int64]:
    """Normalize optional receive timestamps, using ``MISSING_TS_RECV_NS`` for nulls."""
    if series.empty:
        return np.array([], dtype=np.int64)
    output = np.full(len(series), MISSING_TS_RECV_NS, dtype=np.int64)
    valid_mask = series.notna().to_numpy()
    if valid_mask.any():
        output[valid_mask] = normalize_ts_series(series[valid_mask])
    return output


def normalize_price_series(series: pd.Series) -> npt.NDArray[np.int64]:
    """Normalize one Databento price column to fixed-point nanos."""
    if series.empty:
        return np.array([], dtype=np.int64)
    if pd.api.types.is_integer_dtype(series):
        return np.asarray(series.to_numpy(dtype=np.int64, na_value=0), dtype=np.int64)
    if pd.api.types.is_float_dtype(series):
        return np.asarray(
            np.round(series.to_numpy(dtype=np.float64) * 1_000_000_000),
            dtype=np.int64,
        )
    values = series.to_list()
    return np.array([databento_price_to_nanos(value) for value in values], dtype=np.int64)


def normalize_optional_int_series(series: pd.Series, *, default: int = 0) -> npt.NDArray[np.int64]:
    """Normalize optional integer DBN columns."""
    if series.empty:
        return np.array([], dtype=np.int64)
    if pd.api.types.is_integer_dtype(series):
        return np.asarray(series.fillna(default).to_numpy(dtype=np.int64), dtype=np.int64)
    return np.array(
        [databento_optional_int(value, default=default) for value in series.to_list()],
        dtype=np.int64,
    )


def normalize_side_series(series: pd.Series) -> list[str | None]:
    """Map one Databento side column to canonical trade side values."""
    if series.empty:
        return []
    unique_values = series.dropna().unique()
    mapping = {value: map_databento_trade_side(value).value for value in unique_values.tolist()}
    mapping[None] = TradeSide.UNKNOWN.value
    return [
        mapping.get(value, TradeSide.UNKNOWN.value) if value is not None else mapping[None]
        for value in series.to_list()
    ]
