"""Trading session metadata aligned to evaluation timestamps."""

from __future__ import annotations

from datetime import date, datetime

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.time.sessions.constants import RESOLVER_OUTPUT_COLUMNS
from trading_framework.time.sessions.protocol import TradingSessionResolver
from trading_framework.time.utc_datetime_series import utc_datetime_series

_STORED_COLUMNS = ("trading_day", "session_id", "is_rth")
_NAMED_SESSION_COLUMN_PREFIX = "session_"


def _named_session_columns(frame: pl.DataFrame) -> tuple[str, ...]:
    """Additive named-session boolean columns a resolver may carry (ADR-MA-015).

    Anything matching ``session_<name>`` other than the reserved
    ``session_id`` column -- no fixed allow-list to edit per new named
    session.
    """
    return tuple(
        column
        for column in frame.columns
        if column.startswith(_NAMED_SESSION_COLUMN_PREFIX) and column != "session_id"
    )


class TradingSessionMetadata:
    """Session interpretation columns parallel to one market timestamp grid.

    ``resolve`` / ``from_dataframe`` keep the resolver Polars frame and materialize
    Python tuples only when ``trading_days``, ``session_ids``, ``is_rth``, or a
    named session (``named_session(name)``) is read.
    """

    __slots__ = (
        "_frame",
        "_is_rth",
        "_named_session_columns",
        "_named_sessions",
        "_row_count",
        "_session_ids",
        "_trading_days",
    )

    def __init__(self, frame: pl.DataFrame) -> None:
        missing = [column for column in RESOLVER_OUTPUT_COLUMNS if column not in frame.columns]
        if missing:
            msg = f"resolver output missing columns: {missing}"
            raise ValidationError(msg)
        self._named_session_columns = _named_session_columns(frame)
        self._frame = frame.select(*_STORED_COLUMNS, *self._named_session_columns)
        self._row_count = self._frame.height
        self._trading_days: tuple[date, ...] | None = None
        self._session_ids: tuple[str, ...] | None = None
        self._is_rth: tuple[bool, ...] | None = None
        self._named_sessions: dict[str, tuple[bool, ...]] = {}

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

    def named_session(self, name: str) -> tuple[bool, ...]:
        """Membership in a named session (ADR-MA-015), e.g. ``"asia"``, ``"london"``.

        Raises if the resolver this metadata was built from did not carry a
        ``session_<name>`` column -- never silently returns all-``False``.
        """
        column = f"{_NAMED_SESSION_COLUMN_PREFIX}{name}"
        if column not in self._named_session_columns:
            msg = (
                f"named session {name!r} not available on this metadata "
                f"(resolver output carried no {column!r} column) -- configure "
                "a resolver that resolves this named session, e.g. "
                "GlobalSessionCalendarResolver"
            )
            raise ValidationError(msg)
        if column not in self._named_sessions:
            self._named_sessions[column] = tuple(
                bool(value) for value in self._frame[column].to_list()
            )
        return self._named_sessions[column]

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
