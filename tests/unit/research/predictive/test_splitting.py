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


def test_split_mode_is_the_declared_set() -> None:
    assert {member.value for member in PurgedWalkForwardSplitMode} == {
        "ROLLING",
        "EXPANDING",
    }


def test_invalid_split_mode_is_rejected() -> None:
    payload = _valid_split().to_dict()
    payload["mode"] = "K_FOLD"

    with pytest.raises(PredictiveSpecError, match="invalid split mode"):
        PurgedWalkForwardSplitSpec.from_dict(payload)


def test_split_spans_reject_tick() -> None:
    with pytest.raises(PredictiveSpecError, match="test_span must be a bar duration"):
        PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.ROLLING,
            fold_count=2,
            test_span=Timeframe("tick"),
            embargo_span=Timeframe("15m"),
            min_train_rows=10,
        )

    with pytest.raises(PredictiveSpecError, match="embargo_span must be a bar duration"):
        PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.ROLLING,
            fold_count=2,
            test_span=Timeframe("5d"),
            embargo_span=Timeframe("tick"),
            min_train_rows=10,
        )


def test_fold_count_rejects_boolean() -> None:
    payload = _valid_split().to_dict()
    payload["fold_count"] = True

    with pytest.raises(PredictiveSpecError, match="fold_count must be an integer"):
        PurgedWalkForwardSplitSpec.from_dict(payload)


def test_split_spec_from_dict_rejects_missing_field() -> None:
    payload = _valid_split().to_dict()
    del payload["test_span"]

    with pytest.raises(PredictiveSpecError, match="missing field: test_span"):
        PurgedWalkForwardSplitSpec.from_dict(payload)
