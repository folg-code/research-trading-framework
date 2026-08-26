"""Unit tests for LabelSpec."""

from __future__ import annotations

import math

import pytest

from trading_framework.research.predictive import LabelKind, LabelSpec, PredictiveSpecError
from trading_framework.time.models.timeframe import Timeframe


def test_regression_label_is_valid() -> None:
    spec = LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("15m"))

    assert spec.kind is LabelKind.REGRESSION
    assert spec.horizon.value == "15m"
    assert spec.threshold is None
    assert spec.neutral_band is None


def test_binary_label_is_valid() -> None:
    spec = LabelSpec(
        kind=LabelKind.BINARY,
        horizon=Timeframe("15m"),
        threshold=0.0,
    )

    assert spec.kind is LabelKind.BINARY
    assert spec.threshold == 0.0


def test_ternary_label_is_valid() -> None:
    spec = LabelSpec(
        kind=LabelKind.TERNARY,
        horizon=Timeframe("1h"),
        neutral_band=0.001,
    )

    assert spec.kind is LabelKind.TERNARY
    assert spec.neutral_band == 0.001


def test_regression_rejects_threshold() -> None:
    with pytest.raises(PredictiveSpecError, match="must not declare threshold"):
        LabelSpec(
            kind=LabelKind.REGRESSION,
            horizon=Timeframe("15m"),
            threshold=0.0,
        )


def test_binary_requires_finite_threshold() -> None:
    with pytest.raises(PredictiveSpecError, match="BINARY label requires threshold"):
        LabelSpec(kind=LabelKind.BINARY, horizon=Timeframe("15m"))

    with pytest.raises(PredictiveSpecError, match="threshold must be a finite number"):
        LabelSpec(
            kind=LabelKind.BINARY,
            horizon=Timeframe("15m"),
            threshold=math.inf,
        )


def test_binary_rejects_neutral_band() -> None:
    with pytest.raises(PredictiveSpecError, match="must not declare neutral_band"):
        LabelSpec(
            kind=LabelKind.BINARY,
            horizon=Timeframe("15m"),
            threshold=0.0,
            neutral_band=0.001,
        )


def test_ternary_requires_non_negative_band() -> None:
    with pytest.raises(PredictiveSpecError, match="TERNARY label requires neutral_band"):
        LabelSpec(kind=LabelKind.TERNARY, horizon=Timeframe("15m"))

    with pytest.raises(PredictiveSpecError, match="neutral_band must be >= 0"):
        LabelSpec(
            kind=LabelKind.TERNARY,
            horizon=Timeframe("15m"),
            neutral_band=-0.001,
        )


def test_ternary_rejects_threshold() -> None:
    with pytest.raises(PredictiveSpecError, match="must not declare threshold"):
        LabelSpec(
            kind=LabelKind.TERNARY,
            horizon=Timeframe("15m"),
            threshold=0.0,
            neutral_band=0.001,
        )


def test_label_horizon_rejects_tick() -> None:
    with pytest.raises(PredictiveSpecError, match="must be a bar duration"):
        LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("tick"))


def test_label_spec_dict_round_trip() -> None:
    original = LabelSpec(
        kind=LabelKind.TERNARY,
        horizon=Timeframe("30m"),
        neutral_band=0.002,
    )

    restored = LabelSpec.from_dict(original.to_dict())

    assert restored.kind is LabelKind.TERNARY
    assert restored.horizon.value == "30m"
    assert restored.neutral_band == 0.002
    assert restored.threshold is None


def test_regression_and_binary_dict_round_trip() -> None:
    regression = LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("15m"))
    binary = LabelSpec(kind=LabelKind.BINARY, horizon=Timeframe("5m"), threshold=-0.001)

    restored_regression = LabelSpec.from_dict(regression.to_dict())
    restored_binary = LabelSpec.from_dict(binary.to_dict())

    assert restored_regression == regression
    assert "threshold" not in regression.to_dict()
    assert "neutral_band" not in regression.to_dict()
    assert restored_binary == binary
    assert "neutral_band" not in binary.to_dict()


def test_label_kind_is_the_declared_set() -> None:
    assert {member.value for member in LabelKind} == {"REGRESSION", "BINARY", "TERNARY"}


def test_ternary_zero_neutral_band_is_valid() -> None:
    spec = LabelSpec(kind=LabelKind.TERNARY, horizon=Timeframe("15m"), neutral_band=0.0)

    assert spec.neutral_band == 0.0


def test_ternary_rejects_non_finite_band() -> None:
    with pytest.raises(PredictiveSpecError, match="neutral_band must be a finite number"):
        LabelSpec(
            kind=LabelKind.TERNARY,
            horizon=Timeframe("15m"),
            neutral_band=math.nan,
        )


def test_binary_rejects_boolean_threshold() -> None:
    with pytest.raises(PredictiveSpecError, match="threshold must be a finite number"):
        LabelSpec(kind=LabelKind.BINARY, horizon=Timeframe("15m"), threshold=True)


def test_invalid_label_kind_is_rejected() -> None:
    with pytest.raises(PredictiveSpecError, match="invalid label kind"):
        LabelSpec.from_dict({"kind": "MULTICLASS", "horizon": "15m"})


def test_label_spec_from_dict_rejects_missing_field() -> None:
    with pytest.raises(PredictiveSpecError, match="missing field: kind"):
        LabelSpec.from_dict({"horizon": "15m"})


def test_invalid_label_horizon_is_rejected() -> None:
    with pytest.raises(PredictiveSpecError, match="invalid timeframe"):
        LabelSpec.from_dict({"kind": "REGRESSION", "horizon": "15x"})
