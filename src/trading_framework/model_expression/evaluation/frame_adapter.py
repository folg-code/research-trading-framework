"""Convert aligned AnalysisFrame operands to Polars evaluation tables."""

from datetime import UTC, datetime

import numpy as np
import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.time.models.timeframe import Timeframe

_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MICROSECONDS_PER_DAY = 86_400_000_000


def build_evaluation_dataframe(
    frame: AnalysisFrame,
    *,
    evaluation_timeframe: Timeframe,
    column_keys: tuple[str, ...],
) -> pl.DataFrame:
    """Build a Polars table with timestamps, available_at and operand columns."""
    timestamps = _utc_timestamp_series(frame.timestamps)
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


def _utc_timestamp_series(timestamps: tuple[datetime, ...]) -> pl.Series:
    if not timestamps:
        return pl.Series("timestamp", [], dtype=pl.Datetime("us", "UTC"))
    epoch_us = np.fromiter(
        (_utc_epoch_microseconds(timestamp) for timestamp in timestamps),
        dtype=np.int64,
        count=len(timestamps),
    )
    return pl.Series("timestamp", epoch_us, dtype=pl.Datetime("us", "UTC"))


def _utc_epoch_microseconds(timestamp: datetime) -> int:
    tzinfo = timestamp.tzinfo
    if tzinfo is None or tzinfo.utcoffset(timestamp) is None:
        msg = "timestamp must be timezone-aware"
        raise ValidationError(msg)
    utc = timestamp if tzinfo is UTC else timestamp.astimezone(UTC)
    delta = utc - _UNIX_EPOCH
    return delta.days * _MICROSECONDS_PER_DAY + delta.seconds * 1_000_000 + delta.microseconds
