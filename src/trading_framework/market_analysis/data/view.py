"""Read-only canonical market input view."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.models import MarketBar

_OHLCV_FIELDS = frozenset({"open", "high", "low", "close", "volume"})
_RESEARCH_DEFAULT_DTYPE = "float64"


def _as_float64_tuple(values: Iterable[Decimal | float]) -> tuple[float, ...]:
    return tuple(float(value) for value in values)


@dataclass(frozen=True, slots=True)
class DataColumn:
    """Immutable one-dimensional column exposed to analysis components."""

    values: tuple[float, ...]
    dtype: str = _RESEARCH_DEFAULT_DTYPE

    def __post_init__(self) -> None:
        normalized_dtype = self.dtype.strip().lower()
        if not normalized_dtype:
            msg = "dtype must be non-empty"
            raise ValidationError(msg)
        if normalized_dtype != self.dtype:
            object.__setattr__(self, "dtype", normalized_dtype)

    def __len__(self) -> int:
        return len(self.values)


@dataclass(frozen=True, slots=True)
class AnalysisDataView:
    """Read-only OHLCV view aligned to UTC bar timestamps.

    Price columns use ``float64`` (D-027). Volume is exposed as a float64-compatible
    column for backend-neutral adapter consumption.
    """

    timestamps: tuple[datetime, ...]
    open: DataColumn
    high: DataColumn
    low: DataColumn
    close: DataColumn
    volume: DataColumn

    def __post_init__(self) -> None:
        column_lengths = (
            len(self.timestamps),
            len(self.open),
            len(self.high),
            len(self.low),
            len(self.close),
            len(self.volume),
        )
        if len(set(column_lengths)) != 1:
            msg = "all AnalysisDataView columns must share the same length"
            raise ValidationError(msg)

    @classmethod
    def from_bars(cls, bars: Iterable[MarketBar]) -> "AnalysisDataView":
        ordered = tuple(sorted(bars, key=lambda bar: bar.observed_at))
        if not ordered:
            msg = "bars must be non-empty"
            raise ValidationError(msg)

        timestamps = tuple(bar.observed_at for bar in ordered)
        return cls.from_columnar(
            timestamps=timestamps,
            open=_as_float64_tuple(bar.open.value for bar in ordered),
            high=_as_float64_tuple(bar.high.value for bar in ordered),
            low=_as_float64_tuple(bar.low.value for bar in ordered),
            close=_as_float64_tuple(bar.close.value for bar in ordered),
            volume=_as_float64_tuple(float(bar.volume.value) for bar in ordered),
        )

    @classmethod
    def from_columnar(
        cls,
        *,
        timestamps: tuple[datetime, ...],
        open: tuple[float, ...],
        high: tuple[float, ...],
        low: tuple[float, ...],
        close: tuple[float, ...],
        volume: tuple[float, ...],
    ) -> "AnalysisDataView":
        if not timestamps:
            msg = "timestamps must be non-empty"
            raise ValidationError(msg)
        return cls(
            timestamps=timestamps,
            open=DataColumn(open),
            high=DataColumn(high),
            low=DataColumn(low),
            close=DataColumn(close),
            volume=DataColumn(volume),
        )

    def column(self, field: str) -> DataColumn:
        normalized = field.strip().lower()
        columns = {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }
        if normalized not in columns:
            msg = f"unsupported market field: {field!r}"
            raise ValidationError(msg)
        return columns[normalized]

    def __len__(self) -> int:
        return len(self.timestamps)
