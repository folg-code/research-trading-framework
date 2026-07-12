"""Dependency declaration tests."""

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis import (
    ComponentDependency,
    ComponentId,
    ComponentOutputRef,
    DataFieldDependency,
    OutputId,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
)


def test_data_field_dependency_accepts_ohlcv_fields() -> None:
    dep = DataFieldDependency("close")
    assert dep.field == "close"


def test_data_field_dependency_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError, match="unsupported data field"):
        DataFieldDependency("atr")


def test_component_dependency_uses_output_ref_key() -> None:
    params = ParameterSchema(
        fields=(ParameterFieldSpec("period", ParameterType.INT, default=14),)
    ).canonicalize({})
    dep = ComponentDependency(
        output_ref=ComponentOutputRef(
            component_id=ComponentId("volatility.true_range"),
            parameters=params,
            output_id=OutputId("value"),
        )
    )
    assert "volatility.true_range" in dep.canonical_key()
