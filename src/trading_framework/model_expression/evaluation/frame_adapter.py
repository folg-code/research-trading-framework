"""Convert aligned AnalysisFrame operands to Polars evaluation tables."""

import numpy as np
import polars as pl

from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.utc_datetime_series import utc_datetime_series


def build_evaluation_dataframe(
    frame: AnalysisFrame,
    *,
    evaluation_timeframe: Timeframe,
    column_keys: tuple[str, ...],
) -> pl.DataFrame:
    """Build a Polars table with timestamps, available_at and operand columns."""
    timestamps = utc_datetime_series(frame.timestamps)
    operand_series = (
        pl.Series(key, np.asarray(frame.columns[key], dtype=np.float64)) for key in column_keys
    )
    return (
        pl.DataFrame({"timestamp": timestamps})
        .with_columns(
            (pl.col("timestamp") + pl.duration(seconds=evaluation_timeframe.total_seconds)).alias(
                "available_at"
            )
        )
        .with_columns(*operand_series)
    )
