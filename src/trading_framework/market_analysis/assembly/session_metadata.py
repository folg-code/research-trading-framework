"""Trading session metadata aligned to evaluation timestamps."""

from __future__ import annotations

from datetime import date, datetime

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.time.sessions.constants import RESOLVER_OUTPUT_COLUMNS
from trading_framework.time.sessions.protocol import TradingSessionResolver
from trading_framework.time.utc_datetime_series import utc_datetime_series

_STORED_COLUMNS = ("trading_day", "session_id", "is_rth")


class TradingSessionMetadata:
    """Session interpretation columns parallel to one market timestamp grid.

    ``resolve`` / ``from_dataframe`` keep the resolver Polars frame and materialize
    Python tuples only when ``trading_days``, ``session_ids``, or ``is_rth`` are read.
    """

    __slots__ = ("_frame", "_is_rth", "_row_count", "_session_ids", "_trading_days")

    def __init__(self, frame: pl.DataFrame) -> None:
        missing = [column for column in RESOLVER_OUTPUT_COLUMNS if column not in frame.columns]
        if missing:
            msg = f"resolver output missing columns: {missing}"
            raise ValidationError(msg)
        self._frame = frame.select(*_STORED_COLUMNS)
        self._row_count = self._frame.height
        self._trading_days: tuple[date, ...] | None = None
        self._session_ids: tuple[str, ...] | None = None
        self._is_rth: tuple[bool, ...] | None = None

    def __len__(self) -> int:
        return self._row_count

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TradingSessionMetadata):
            return NotImplemented
        return self._frame.equals(other._frame)

    @property
    def trading_days(self) -> tuple[date, ...]:
        if self._trading_days is None:
            self._trading_days = tuple(self._frame["trading_day"].to_list())
        return self._trading_days

    @property
    def session_ids(self) -> tuple[str, ...]:
        if self._session_ids is None:
            self._session_ids = tuple(str(value) for value in self._frame["session_id"].to_list())
        return self._session_ids

    @property
    def is_rth(self) -> tuple[bool, ...]:
        if self._is_rth is None:
            self._is_rth = tuple(bool(value) for value in self._frame["is_rth"].to_list())
        return self._is_rth

    @classmethod
    def from_dataframe(cls, frame: pl.DataFrame) -> TradingSessionMetadata:
        return cls(frame)

    @classmethod
    def resolve(
        cls,
        timestamps: tuple[datetime, ...],
        resolver: TradingSessionResolver,
    ) -> TradingSessionMetadata:
        if not timestamps:
            msg = "timestamps must be non-empty"
            raise ValidationError(msg)
        frame = resolver.resolve(utc_datetime_series(timestamps))
        if frame.height != len(timestamps):
            msg = "resolver output length must match evaluation timestamps"
            raise ValidationError(msg)
        return cls.from_dataframe(frame)
