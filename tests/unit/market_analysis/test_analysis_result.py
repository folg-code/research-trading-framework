"""Analysis result, lineage, and availability tests."""

from datetime import UTC, datetime

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis import (
    AnalysisResult,
    AvailabilityMetadata,
    AvailabilityPolicy,
    ComponentId,
    ComponentVersion,
    ComputationIdentity,
    ImplementationId,
    ImplementationVersion,
    Lineage,
    OutputFieldSpec,
    OutputGroup,
    OutputId,
    OutputSchema,
    OutputSeries,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
    TimeRange,
    ValidityMetadata,
    WarmUpMetadata,
)
from trading_framework.time.models.timeframe import Timeframe


def _build_result() -> AnalysisResult:
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
    time_range = TimeRange(
        start=datetime(2024, 1, 1, tzinfo=UTC),
        end=datetime(2024, 1, 2, tzinfo=UTC),
    )
    identity = ComputationIdentity(
        component_id=ComponentId("volatility.atr"),
        component_version=ComponentVersion("1.0.0"),
        implementation_id=ImplementationId("numpy.atr"),
        implementation_version=ImplementationVersion("1.0.0"),
        parameters=params,
        dataset_ref=dataset_ref,
        computation_timeframe=Timeframe("1m"),
        requested_range=time_range,
        dependency_keys=("volatility.true_range:{}",),
    )
    output_id = OutputId("value")
    schema = OutputSchema(outputs=(OutputFieldSpec(output_id, "float64", OutputGroup.CORE),))
    lineage = Lineage(
        dataset_ref=dataset_ref,
        component_id=identity.component_id,
        component_version=identity.component_version,
        implementation_id=identity.implementation_id,
        implementation_version=identity.implementation_version,
        parameters=params,
        dependency_keys=identity.dependency_keys,
        engine_version="0.1.0",
        executed_at=datetime(2024, 1, 3, tzinfo=UTC),
    )
    return AnalysisResult(
        computation_identity=identity,
        output_schema=schema,
        outputs={output_id: OutputSeries(values=(1.0, 2.0, 3.0))},
        lineage=lineage,
        validity=ValidityMetadata(valid_from_index=0, valid_to_index=2),
        warmup=WarmUpMetadata(warmup_bars=0, valid_from_index=0, valid_to_index=2),
        availability=AvailabilityMetadata(policy=AvailabilityPolicy.SAME_BAR),
        diagnostics={"backend": "numpy"},
    )


def test_analysis_result_requires_outputs_matching_schema() -> None:
    result = _build_result()
    assert result.lineage.to_json_dict()["component_id"] == "volatility.atr"


def test_analysis_result_rejects_output_schema_mismatch() -> None:
    result = _build_result()
    with pytest.raises(ValidationError, match="outputs must match"):
        AnalysisResult(
            computation_identity=result.computation_identity,
            output_schema=result.output_schema,
            outputs={},
            lineage=result.lineage,
            validity=result.validity,
            warmup=result.warmup,
            availability=result.availability,
            diagnostics={},
        )


def test_lineage_is_json_serializable_dict() -> None:
    result = _build_result()
    payload = result.lineage.to_json_dict()
    assert payload["dataset_ref"]
    assert payload["parameters"] == {"period": 14}
