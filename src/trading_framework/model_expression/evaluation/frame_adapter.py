"""Convert aligned AnalysisFrame operands to Polars evaluation tables."""

from datetime import datetime

import polars as pl

from trading_framework.market.temporal import derive_bar_interval
from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.time.models.timeframe import Timeframe


def build_evaluation_dataframe(
    frame: AnalysisFrame,
    *,
    evaluation_timeframe: Timeframe,
    column_keys: tuple[str, ...],
) -> pl.DataFrame:
    """Build a Polars table with timestamps, available_at and operand columns."""
    timestamps = list(frame.timestamps)
    available_at = [
        derive_bar_interval(timestamp, evaluation_timeframe)[1] for timestamp in timestamps
    ]
    data: dict[str, list[datetime] | list[float]] = {
        "timestamp": timestamps,
        "available_at": available_at,
    }
    for key in column_keys:
        data[key] = list(frame.columns[key])
    return pl.DataFrame(data)
