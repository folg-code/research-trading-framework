"""Align canonical OHLCV columns to an evaluation AnalysisFrame grid."""

from __future__ import annotations

import math
from datetime import datetime

from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.market_analysis.data.view import AnalysisDataView

_OHLCV_FIELDS = ("open", "high", "low", "close", "volume")


def align_ohlcv_to_evaluation_frame(
    frame: AnalysisFrame,
    market_view: AnalysisDataView,
) -> dict[str, tuple[float, ...]]:
    """Return OHLCV tuples indexed by ``frame.timestamps``."""
    if "close" in frame.columns:
        return {field: frame.columns[field] for field in _OHLCV_FIELDS if field in frame.columns}

    index_by_timestamp = {
        timestamp: index for index, timestamp in enumerate(market_view.timestamps)
    }
    columns: dict[str, list[float]] = {field: [] for field in _OHLCV_FIELDS}
    for timestamp in frame.timestamps:
        index = index_by_timestamp.get(timestamp)
        if index is None:
            for values in columns.values():
                values.append(math.nan)
            continue
        columns["open"].append(market_view.open.values[index])
        columns["high"].append(market_view.high.values[index])
        columns["low"].append(market_view.low.values[index])
        columns["close"].append(market_view.close.values[index])
        columns["volume"].append(market_view.volume.values[index])
    return {field: tuple(values) for field, values in columns.items()}


def timestamp_index(frame: AnalysisFrame) -> dict[datetime, int]:
    """Map evaluation timestamps to row indices."""
    return {timestamp: index for index, timestamp in enumerate(frame.timestamps)}
