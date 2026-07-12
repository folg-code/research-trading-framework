"""Output identity and schema tests."""

from datetime import UTC, datetime

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis import (
    ComponentId,
    ComponentOutputRef,
    ComponentVersion,
    ComputationIdentity,
    ImplementationId,
    ImplementationVersion,
    OutputFieldSpec,
    OutputGroup,
    OutputId,
    OutputRef,
    OutputSchema,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
    TimeRange,
)
from trading_framework.time.models.timeframe import Timeframe


def test_output_schema_rejects_duplicate_output_ids() -> None:
    value = OutputId("value")
    with pytest.raises(ValidationError, match="duplicate output ids"):
        OutputSchema(
            outputs=(
                OutputFieldSpec(value, "float64", OutputGroup.CORE),
                OutputFieldSpec(value, "float64", OutputGroup.DIAGNOSTIC),
            )
        )


def test_component_output_ref_targets_named_output() -> None:
    params = ParameterSchema(
        fields=(ParameterFieldSpec("period", ParameterType.INT, default=14),)
    ).canonicalize({})
    ref = ComponentOutputRef(
        component_id=ComponentId("volatility.atr"),
        parameters=params,
        output_id=OutputId("value"),
    )
    assert "volatility.atr" in ref.canonical_key()


def test_output_ref_uses_resolved_computation_identity() -> None:
    dataset_ref = DatasetRef(
        DatasetId(
            instrument_id=Identifier("NQ.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id="sample",
        ),
        version=1,
    )
    params = ParameterSchema(
        fields=(ParameterFieldSpec("period", ParameterType.INT, default=14),)
    ).canonicalize({})
    identity = ComputationIdentity(
        component_id=ComponentId("volatility.atr"),
        component_version=ComponentVersion("1.0.0"),
        implementation_id=ImplementationId("numpy.atr"),
        implementation_version=ImplementationVersion("1.0.0"),
        parameters=params,
        dataset_ref=dataset_ref,
        computation_timeframe=Timeframe("1m"),
        requested_range=TimeRange(
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        ),
        dependency_keys=(),
    )
    ref = OutputRef(computation_identity=identity, output_id=OutputId("value"))
    assert ref.output_id.value == "value"
