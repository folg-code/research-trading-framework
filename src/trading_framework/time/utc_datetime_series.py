"""Convert timezone-aware datetime tuples into UTC Polars Series."""

from datetime import UTC, datetime

import numpy as np
import polars as pl

from trading_framework.core.exceptions import ValidationError

_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MICROSECONDS_PER_DAY = 86_400_000_000


def utc_datetime_series(timestamps: tuple[datetime, ...]) -> pl.Series:
    """Build a UTC microsecond Series named ``timestamp`` from aware datetimes."""
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
