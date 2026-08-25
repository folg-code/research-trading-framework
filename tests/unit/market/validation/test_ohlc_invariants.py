"""Vectorized OHLC invariant tests matching MarketBar rules."""

from __future__ import annotations

import numpy as np
import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.validation import assert_ohlc_invariants


def test_assert_ohlc_invariants_accepts_valid_columns() -> None:
    assert_ohlc_invariants(
        open=(100.0, 101.0),
        high=(105.0, 102.0),
        low=(99.0, 100.5),
        close=(103.0, 101.5),
    )


def test_assert_ohlc_invariants_rejects_high_below_open_or_close() -> None:
    with pytest.raises(ValidationError, match="high must be >= open and close"):
        assert_ohlc_invariants(
            open=(100.0,),
            high=(99.0,),
            low=(98.0,),
            close=(99.5,),
        )


def test_assert_ohlc_invariants_rejects_low_above_open_or_close() -> None:
    with pytest.raises(ValidationError, match="low must be <= open and close"):
        assert_ohlc_invariants(
            open=(100.0,),
            high=(101.0,),
            low=(100.5,),
            close=(100.2,),
        )


def test_assert_ohlc_invariants_rejects_high_below_open_even_when_also_below_low() -> None:
    with pytest.raises(ValidationError, match="high must be >= open and close"):
        assert_ohlc_invariants(
            open=(100.0,),
            high=(99.0,),
            low=(101.0,),
            close=(100.0,),
        )


def test_assert_ohlc_invariants_rejects_non_finite_values() -> None:
    with pytest.raises(ValidationError, match="finite"):
        assert_ohlc_invariants(
            open=(100.0,),
            high=(np.inf,),
            low=(99.0,),
            close=(100.0,),
        )


def test_assert_ohlc_invariants_rejects_length_mismatch() -> None:
    with pytest.raises(ValidationError, match="same length"):
        assert_ohlc_invariants(
            open=(100.0, 101.0),
            high=(105.0,),
            low=(99.0, 100.0),
            close=(103.0, 101.0),
        )
