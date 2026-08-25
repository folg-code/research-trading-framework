"""Columnar resample path: no MarketBar round-trip, same analysis-view facts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import polars as pl
import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketBar
from trading_framework.market.temporal.bar_interval import derive_bar_interval
from trading_framework.market_analysis.data.resample import (
    analysis_view_to_polars,
    resample_analysis_view,
    resample_ohlcv_dataframe,
)
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.models.resample import ResampleSpec
from trading_framework.time.models.timeframe import Timeframe


def _utc(minute: int) -> datetime:
    return datetime(2024, 6, 3, 10, minute, tzinfo=UTC)


def _bar(minute: int, *, price: float) -> MarketBar:
    observed_at = _utc(minute)
    value = Decimal(str(price))
    return MarketBar(
        open=Price(value),
        high=Price(value + Decimal("1")),
        low=Price(value - Decimal("1")),
        close=Price(value),
        volume=Volume(10),
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
    )


def _legacy_view_from_resampled_frame(
    frame: pl.DataFrame,
    timeframe: Timeframe,
) -> AnalysisDataView:
    bars: list[MarketBar] = []
    for row in frame.iter_rows(named=True):
        observed = row["observed_at"]
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
    return AnalysisDataView.from_bars(bars)


def test_resample_analysis_view_matches_legacy_market_bar_round_trip() -> None:
    source = AnalysisDataView.from_bars(
        tuple(_bar(index, price=100.0 + index) for index in range(15))
    )
    spec = ResampleSpec(target_timeframe=Timeframe("5m"))
    columnar = resample_analysis_view(source, spec)
    legacy = _legacy_view_from_resampled_frame(
        resample_ohlcv_dataframe(analysis_view_to_polars(source), spec),
        spec.target_timeframe,
    )
    assert columnar.timestamps == legacy.timestamps
    assert columnar.open.values == legacy.open.values
    assert columnar.high.values == legacy.high.values
    assert columnar.low.values == legacy.low.values
    assert columnar.close.values == legacy.close.values
    assert columnar.volume.values == legacy.volume.values


def test_resample_analysis_view_rejects_invalid_ohlc() -> None:
    observed_at = _utc(0)
    invalid = AnalysisDataView.from_columnar(
        timestamps=(observed_at,),
        open=(100.0,),
        high=(99.0,),
        low=(98.0,),
        close=(99.5,),
        volume=(1.0,),
    )
    with pytest.raises(ValidationError, match="high must be >= open and close"):
        resample_analysis_view(invalid, ResampleSpec(target_timeframe=Timeframe("5m")))


def test_resample_analysis_view_rejects_negative_volume() -> None:
    observed_at = _utc(0)
    invalid = AnalysisDataView.from_columnar(
        timestamps=(observed_at,),
        open=(100.0,),
        high=(101.0,),
        low=(99.0,),
        close=(100.5,),
        volume=(-1.0,),
    )
    with pytest.raises(ValidationError, match="volume must be non-negative"):
        resample_analysis_view(invalid, ResampleSpec(target_timeframe=Timeframe("5m")))
