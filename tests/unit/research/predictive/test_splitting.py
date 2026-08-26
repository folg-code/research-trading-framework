"""Unit tests for PurgedWalkForwardSplitSpec."""

from __future__ import annotations

import pytest

from trading_framework.research.predictive import (
    PredictiveSpecError,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
)
from trading_framework.time.models.timeframe import Timeframe


def _valid_split() -> PurgedWalkForwardSplitSpec:
    return PurgedWalkForwardSplitSpec(
        mode=PurgedWalkForwardSplitMode.EXPANDING,
        fold_count=4,
        test_span=Timeframe("20d"),
        embargo_span=Timeframe("15m"),
        min_train_rows=500,
    )


def test_split_spec_is_valid() -> None:
    spec = _valid_split()

    assert spec.mode is PurgedWalkForwardSplitMode.EXPANDING
    assert spec.fold_count == 4
    assert spec.embargo_span.value == "15m"


def test_zero_embargo_span_is_allowed() -> None:
    spec = PurgedWalkForwardSplitSpec(
        mode=PurgedWalkForwardSplitMode.ROLLING,
        fold_count=2,
        test_span=Timeframe("5d"),
        embargo_span=Timeframe("0m"),
        min_train_rows=1,
    )

    assert spec.embargo_span.total_seconds == 0


def test_fold_count_must_be_positive() -> None:
    with pytest.raises(PredictiveSpecError, match="fold_count must be at least 1"):
        PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.ROLLING,
            fold_count=0,
            test_span=Timeframe("5d"),
            embargo_span=Timeframe("15m"),
            min_train_rows=10,
        )


def test_min_train_rows_must_be_positive() -> None:
    with pytest.raises(PredictiveSpecError, match="min_train_rows must be at least 1"):
        PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.ROLLING,
            fold_count=2,
            test_span=Timeframe("5d"),
            embargo_span=Timeframe("15m"),
            min_train_rows=0,
        )


def test_test_span_must_be_positive() -> None:
    with pytest.raises(PredictiveSpecError, match="test_span must be a positive duration"):
        PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.ROLLING,
            fold_count=2,
            test_span=Timeframe("0m"),
            embargo_span=Timeframe("15m"),
            min_train_rows=10,
        )


def test_split_spec_dict_round_trip() -> None:
    original = _valid_split()

    restored = PurgedWalkForwardSplitSpec.from_dict(original.to_dict())

    assert restored == original
