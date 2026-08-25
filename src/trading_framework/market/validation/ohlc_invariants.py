"""Vectorized OHLC invariants matching ``MarketBar.__post_init__``."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from trading_framework.core.exceptions import ValidationError

_FloatColumn = Sequence[float] | NDArray[np.floating]


def _as_float64(values: _FloatColumn, *, name: str) -> NDArray[np.float64]:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1:
        msg = f"{name} must be a one-dimensional column"
        raise ValidationError(msg)
    return array


def assert_ohlc_invariants(
    *,
    open: _FloatColumn,
    high: _FloatColumn,
    low: _FloatColumn,
    close: _FloatColumn,
) -> None:
    """Raise ``ValidationError`` if any row violates MarketBar OHLC rules.

    Checks match ``MarketBar.__post_init__``: high >= open and close, low <= open
    and close, and high >= low. Applied to whole columns instead of per-bar objects.
    """
    open_arr = _as_float64(open, name="open")
    high_arr = _as_float64(high, name="high")
    low_arr = _as_float64(low, name="low")
    close_arr = _as_float64(close, name="close")
    if not (len(open_arr) == len(high_arr) == len(low_arr) == len(close_arr)):
        msg = "OHLC columns must share the same length"
        raise ValidationError(msg)
    if len(open_arr) == 0:
        return
    if not (
        np.isfinite(open_arr).all()
        and np.isfinite(high_arr).all()
        and np.isfinite(low_arr).all()
        and np.isfinite(close_arr).all()
    ):
        msg = "OHLC values must be finite"
        raise ValidationError(msg)
    if bool(((high_arr < open_arr) | (high_arr < close_arr)).any()):
        msg = "high must be >= open and close"
        raise ValidationError(msg)
    if bool(((low_arr > open_arr) | (low_arr > close_arr)).any()):
        msg = "low must be <= open and close"
        raise ValidationError(msg)
    if bool((high_arr < low_arr).any()):
        msg = "high must be >= low"
        raise ValidationError(msg)
