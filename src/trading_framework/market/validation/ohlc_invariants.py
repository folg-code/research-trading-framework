"""Vectorized OHLC invariants matching ``MarketBar.__post_init__``."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.validation.protocols import (
    ValidationIssue,
    ValidationSeverity,
)

_FloatColumn = Sequence[float] | NDArray[np.floating]


def _as_float64(values: _FloatColumn, *, name: str) -> NDArray[np.float64]:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1:
        msg = f"{name} must be a one-dimensional column"
        raise ValidationError(msg)
    return array


def ohlc_invariant_issues(
    *,
    open: _FloatColumn,
    high: _FloatColumn,
    low: _FloatColumn,
    close: _FloatColumn,
) -> tuple[ValidationIssue, ...]:
    """Return MarketBar OHLC violations as row-level issues (1-based row numbers)."""
    open_arr = _as_float64(open, name="open")
    high_arr = _as_float64(high, name="high")
    low_arr = _as_float64(low, name="low")
    close_arr = _as_float64(close, name="close")
    if not (len(open_arr) == len(high_arr) == len(low_arr) == len(close_arr)):
        msg = "OHLC columns must share the same length"
        raise ValidationError(msg)
    if len(open_arr) == 0:
        return ()

    issues: list[ValidationIssue] = []
    finite_mask = (
        np.isfinite(open_arr)
        & np.isfinite(high_arr)
        & np.isfinite(low_arr)
        & np.isfinite(close_arr)
    )
    for index in np.flatnonzero(~finite_mask):
        issues.append(
            ValidationIssue(
                message="OHLC values must be finite",
                severity=ValidationSeverity.ERROR,
                row_number=int(index) + 1,
            )
        )

    high_lt_open_or_close = (high_arr < open_arr) | (high_arr < close_arr)
    low_gt_open_or_close = (low_arr > open_arr) | (low_arr > close_arr)
    high_lt_low = high_arr < low_arr
    for row_index in range(len(open_arr)):
        if not finite_mask[row_index]:
            continue
        row_number = row_index + 1
        if high_lt_open_or_close[row_index]:
            issues.append(
                ValidationIssue(
                    message="high must be >= open and close",
                    severity=ValidationSeverity.ERROR,
                    row_number=row_number,
                    field="high",
                )
            )
            continue
        if low_gt_open_or_close[row_index]:
            issues.append(
                ValidationIssue(
                    message="low must be <= open and close",
                    severity=ValidationSeverity.ERROR,
                    row_number=row_number,
                    field="low",
                )
            )
            continue
        if high_lt_low[row_index]:
            issues.append(
                ValidationIssue(
                    message="high must be >= low",
                    severity=ValidationSeverity.ERROR,
                    row_number=row_number,
                    field="high",
                )
            )
    return tuple(issues)


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
    issues = ohlc_invariant_issues(open=open, high=high, low=low, close=close)
    if issues:
        raise ValidationError(issues[0].message)
