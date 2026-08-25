"""Polars OHLCV resampling for multitimeframe batch analysis."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, cast

import numpy as np
import polars as pl
from numpy.typing import NDArray

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.validation import assert_ohlc_invariants
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.models.resample import ResampleSpec

_OHLCV_COLUMNS = ("open", "high", "low", "close", "volume")


def analysis_view_to_polars(view: AnalysisDataView) -> pl.DataFrame:
    """Convert a read-only analysis view to a Polars frame without mutating the view."""
    return pl.DataFrame(
        {
            "observed_at": list(view.timestamps),
            "open": list(view.open.values),
            "high": list(view.high.values),
            "low": list(view.low.values),
            "close": list(view.close.values),
            "volume": list(view.volume.values),
        }
    )


def resample_ohlcv_dataframe(source: pl.DataFrame, spec: ResampleSpec) -> pl.DataFrame:
    """Resample OHLCV rows using fixed UTC left-labeled bucket semantics."""
    if source.is_empty():
        msg = "source frame must be non-empty"
        raise ValidationError(msg)
    if "observed_at" not in source.columns:
        msg = "source frame must include observed_at"
        raise ValidationError(msg)

    working = source.sort("observed_at")
    closed = cast(Literal["left", "right", "both", "none"], spec.closed)
    label = cast(Literal["left", "right", "datapoint"], spec.label)
    resampled = (
        working.group_by_dynamic(
            "observed_at",
            every=spec.target_timeframe.value,
            closed=closed,
            label=label,
        )
        .agg(
            pl.col("open").first().alias("open"),
            pl.col("high").max().alias("high"),
            pl.col("low").min().alias("low"),
            pl.col("close").last().alias("close"),
            pl.col("volume").sum().alias("volume"),
        )
        .sort("observed_at")
    )
    if resampled.is_empty():
        msg = "resampling produced no rows"
        raise ValidationError(msg)
    return resampled


def _float_column(frame: pl.DataFrame, name: str) -> NDArray[np.float64]:
    return np.asarray(frame[name].to_numpy(), dtype=np.float64)


def _analysis_view_from_ohlcv_frame(frame: pl.DataFrame) -> AnalysisDataView:
    """Build an analysis view from resampled columns without ``MarketBar`` objects."""
    timestamps = frame["observed_at"].to_list()
    if not timestamps or not all(isinstance(value, datetime) for value in timestamps):
        msg = "observed_at must be datetime"
        raise TypeError(msg)
    open_values = _float_column(frame, "open")
    high_values = _float_column(frame, "high")
    low_values = _float_column(frame, "low")
    close_values = _float_column(frame, "close")
    volume_values = _float_column(frame, "volume")
    assert_ohlc_invariants(
        open=open_values,
        high=high_values,
        low=low_values,
        close=close_values,
    )
    if bool((volume_values < 0).any()):
        msg = "volume must be non-negative"
        raise ValidationError(msg)
    return AnalysisDataView.from_columnar(
        timestamps=tuple(timestamps),
        open=tuple(float(value) for value in open_values),
        high=tuple(float(value) for value in high_values),
        low=tuple(float(value) for value in low_values),
        close=tuple(float(value) for value in close_values),
        volume=tuple(float(value) for value in volume_values),
    )


def resample_analysis_view(source: AnalysisDataView, spec: ResampleSpec) -> AnalysisDataView:
    """Resample one analysis view and return a new immutable view."""
    source_frame = analysis_view_to_polars(source)
    resampled_frame = resample_ohlcv_dataframe(source_frame, spec)
    return _analysis_view_from_ohlcv_frame(resampled_frame)


def verify_source_frame_unchanged(before: pl.DataFrame, after: pl.DataFrame) -> bool:
    """Return whether resampling left the source Polars frame unchanged."""
    if before.columns != after.columns:
        return False
    for column in _OHLCV_COLUMNS:
        if before[column].to_list() != after[column].to_list():
            return False
    return before["observed_at"].to_list() == after["observed_at"].to_list()
