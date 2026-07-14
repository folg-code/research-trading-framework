"""Columnar OHLCV batches for batch research without per-bar domain objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.models.time_range import TimeRange


@dataclass(frozen=True, slots=True)
class OhlcvColumnBatch:
    """Sorted OHLCV columns materialized once from storage."""

    timestamps: tuple[datetime, ...]
    available_at: tuple[datetime, ...]
    open: tuple[float, ...]
    high: tuple[float, ...]
    low: tuple[float, ...]
    close: tuple[float, ...]
    volume: tuple[float, ...]

    def __post_init__(self) -> None:
        lengths = (
            len(self.timestamps),
            len(self.available_at),
            len(self.open),
            len(self.high),
            len(self.low),
            len(self.close),
            len(self.volume),
        )
        if len(set(lengths)) != 1:
            msg = "columnar OHLCV columns must share the same length"
            raise ValueError(msg)

    def to_analysis_view(self) -> AnalysisDataView:
        return AnalysisDataView.from_columnar(
            timestamps=self.timestamps,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
        )

    def slice_observed_range(self, time_range: TimeRange) -> OhlcvColumnBatch:
        indices = [
            index
            for index, timestamp in enumerate(self.timestamps)
            if time_range.start <= timestamp <= time_range.end
        ]
        if not indices:
            return _empty_column_batch()
        return OhlcvColumnBatch(
            timestamps=tuple(self.timestamps[index] for index in indices),
            available_at=tuple(self.available_at[index] for index in indices),
            open=tuple(self.open[index] for index in indices),
            high=tuple(self.high[index] for index in indices),
            low=tuple(self.low[index] for index in indices),
            close=tuple(self.close[index] for index in indices),
            volume=tuple(self.volume[index] for index in indices),
        )


def _empty_column_batch() -> OhlcvColumnBatch:
    return OhlcvColumnBatch(
        timestamps=(),
        available_at=(),
        open=(),
        high=(),
        low=(),
        close=(),
        volume=(),
    )
