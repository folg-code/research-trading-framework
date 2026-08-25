"""CME ES regular trading hours session resolver."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.time.sessions.constants import (
    ES_RTH_SESSION_ID,
    OUTSIDE_RTH_SESSION_ID,
)

_NY_TIMEZONE = "America/New_York"


def _validate_timestamps(timestamps: pl.Series) -> None:
    if timestamps.is_empty():
        msg = "timestamps must be non-empty"
        raise ValidationError(msg)
    if not timestamps.dtype.is_temporal():
        msg = "timestamps must be a datetime Series"
        raise ValidationError(msg)
    time_zone = getattr(timestamps.dtype, "time_zone", None)
    if time_zone is not None and time_zone != "UTC":
        msg = "timestamps must use UTC timezone"
        raise ValidationError(msg)


@dataclass(frozen=True, slots=True)
class CmeEsRthSessionResolver:
    """Resolve CME ES RTH membership using an owned 09:30-16:00 America/New_York window.

    This is **not** CMES Globex availability. Optional ``holiday_dates`` mask weekdays
    that would otherwise qualify as RTH (for example US equity holidays from XNYS).
    """

    holiday_dates: frozenset[date] | None = None

    def resolve(self, timestamps: pl.Series) -> pl.DataFrame:
        _validate_timestamps(timestamps)
        is_rth = (
            (pl.col("weekday") <= 5)
            & ((pl.col("hour") > 9) | ((pl.col("hour") == 9) & (pl.col("minute") >= 30)))
            & (pl.col("hour") < 16)
        )
        if self.holiday_dates:
            is_rth = is_rth & ~pl.col("trading_day").is_in(list(self.holiday_dates))
        output = (
            pl.DataFrame({"timestamp": timestamps})
            .with_columns(
                pl.col("timestamp").dt.convert_time_zone(_NY_TIMEZONE).alias("ny_ts"),
            )
            .with_columns(
                pl.col("ny_ts").dt.date().alias("trading_day"),
                pl.col("ny_ts").dt.weekday().alias("weekday"),
                pl.col("ny_ts").dt.hour().alias("hour"),
                pl.col("ny_ts").dt.minute().alias("minute"),
            )
            .select(
                "timestamp",
                "trading_day",
                pl.when(is_rth)
                .then(pl.lit(ES_RTH_SESSION_ID))
                .otherwise(pl.lit(OUTSIDE_RTH_SESSION_ID))
                .alias("session_id"),
                is_rth.alias("is_rth"),
            )
        )
        if output.height != timestamps.len():
            msg = "resolver output length must match input timestamps"
            raise ValidationError(msg)
        return output
