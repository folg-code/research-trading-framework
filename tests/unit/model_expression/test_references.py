"""Tests for model expression references."""

from unittest.mock import MagicMock

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis import OutputId
from trading_framework.market_analysis.components.volatility import VolatilityStateComponent
from trading_framework.model_expression import (
    ComponentOutputReference,
    MarketField,
    MarketFieldReference,
)
from trading_framework.time.models.timeframe import Timeframe


def test_market_field_reference_frame_column_key() -> None:
    reference = MarketFieldReference(field=MarketField.CLOSE)
    assert reference.frame_column_key() == "close"
    assert reference.dependency_key() == "market:close"


def test_component_output_reference_maps_to_request_and_frame_spec() -> None:
    component = VolatilityStateComponent()
    parameters = component.parameter_schema.canonicalize({"period": 14, "threshold": 5.0})
    reference = ComponentOutputReference(
        component_id=component.component_id,
        parameters=parameters,
        output_id=OutputId("state"),
        computation_timeframe=Timeframe("5m"),
        alias="vol_state",
    )

    request = reference.to_component_request()
    assert request.component_id == component.component_id
    assert request.parameters == parameters
    assert request.computation_timeframe == Timeframe("5m")

    spec = reference.to_frame_column_spec()
    assert spec.alias == "vol_state"
    assert spec.output_id == OutputId("state")


def test_component_output_reference_resolves_explicit_alias() -> None:
    component = VolatilityStateComponent()
    parameters = component.parameter_schema.canonicalize({"period": 14, "threshold": 5.0})
    reference = ComponentOutputReference(
        component_id=component.component_id,
        parameters=parameters,
        output_id=OutputId("state"),
        alias="vol_state",
    )
    assert reference.resolve_frame_column_key(computation_identity=MagicMock()) == "vol_state"


def test_component_output_reference_rejects_blank_alias() -> None:
    component = VolatilityStateComponent()
    parameters = component.parameter_schema.canonicalize({"period": 14})
    with pytest.raises(ValidationError, match="alias must be non-empty"):
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=parameters,
            output_id=OutputId("state"),
            alias="   ",
        )
