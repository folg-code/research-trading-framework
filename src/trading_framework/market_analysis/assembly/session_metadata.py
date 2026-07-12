"""Trading session metadata aligned to evaluation timestamps."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.time.sessions.constants import RESOLVER_OUTPUT_COLUMNS
from trading_framework.time.sessions.protocol import TradingSessionResolver


@dataclass(frozen=True, slots=True)
class TradingSessionMetadata:
    """Session interpretation columns parallel to one market timestamp grid."""

    trading_days: tuple[date, ...]
    session_ids: tuple[str, ...]
    is_rth: tuple[bool, ...]

    def __post_init__(self) -> None:
        lengths = {len(self.trading_days), len(self.session_ids), len(self.is_rth)}
        if len(lengths) != 1:
            msg = "session metadata columns must share the same length"
            raise ValidationError(msg)

    def __len__(self) -> int:
        return len(self.trading_days)

    @classmethod
    def from_dataframe(cls, frame: pl.DataFrame) -> TradingSessionMetadata:
        missing = [column for column in RESOLVER_OUTPUT_COLUMNS if column not in frame.columns]
        if missing:
            msg = f"resolver output missing columns: {missing}"
            raise ValidationError(msg)
        return cls(
            trading_days=tuple(frame["trading_day"].to_list()),
            session_ids=tuple(str(value) for value in frame["session_id"].to_list()),
            is_rth=tuple(bool(value) for value in frame["is_rth"].to_list()),
        )

    @classmethod
    def resolve(
        cls,
        timestamps: tuple[datetime, ...],
        resolver: TradingSessionResolver,
    ) -> TradingSessionMetadata:
        if not timestamps:
            msg = "timestamps must be non-empty"
            raise ValidationError(msg)
        frame = resolver.resolve(pl.Series("timestamp", timestamps))
        if frame.height != len(timestamps):
            msg = "resolver output length must match evaluation timestamps"
            raise ValidationError(msg)
        return cls.from_dataframe(frame)
