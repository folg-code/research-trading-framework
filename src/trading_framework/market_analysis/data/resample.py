"""Polars OHLCV resampling for multitimeframe batch analysis."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, cast

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketBar
from trading_framework.market.temporal.bar_interval import derive_bar_interval
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.models.resample import ResampleSpec
from trading_framework.time.models.timeframe import Timeframe

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


def polars_ohlcv_to_market_bars(
    frame: pl.DataFrame,
    *,
    timeframe: Timeframe,
) -> tuple[MarketBar, ...]:
    """Convert resampled OHLCV rows to canonical market bars."""
    bars: list[MarketBar] = []
    for row in frame.iter_rows(named=True):
        observed = row["observed_at"]
        if not isinstance(observed, datetime):
            msg = "observed_at must be datetime"
            raise TypeError(msg)
        _, available_at = derive_bar_interval(observed, timeframe)
        bars.append(
            MarketBar(
                open=Price(Decimal(str(row["open"]))),
                high=Price(Decimal(str(row["high"]))),
                low=Price(Decimal(str(row["low"]))),
                close=Price(Decimal(str(row["close"]))),
                volume=Volume(int(row["volume"])),
                observed_at=observed,
                available_at=available_at,
            )
        )
    return tuple(bars)


def resample_analysis_view(source: AnalysisDataView, spec: ResampleSpec) -> AnalysisDataView:
    """Resample one analysis view and return a new immutable view."""
    source_frame = analysis_view_to_polars(source)
    resampled_frame = resample_ohlcv_dataframe(source_frame, spec)
    bars = polars_ohlcv_to_market_bars(resampled_frame, timeframe=spec.target_timeframe)
    return AnalysisDataView.from_bars(bars)


def verify_source_frame_unchanged(before: pl.DataFrame, after: pl.DataFrame) -> bool:
    """Return whether resampling left the source Polars frame unchanged."""
    if before.columns != after.columns:
        return False
    for column in _OHLCV_COLUMNS:
        if before[column].to_list() != after[column].to_list():
            return False
    return before["observed_at"].to_list() == after["observed_at"].to_list()
