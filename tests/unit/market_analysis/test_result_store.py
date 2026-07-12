"""AnalysisResultStore tests."""

from datetime import UTC, datetime

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis import (
    AnalysisResult,
    AvailabilityMetadata,
    AvailabilityPolicy,
    CanonicalParameters,
    ComponentId,
    ComponentVersion,
    ComputationIdentity,
    ImplementationId,
    ImplementationVersion,
    Lineage,
    OutputFieldSpec,
    OutputId,
    OutputRef,
    OutputSchema,
    OutputSeries,
    TimeRange,
    ValidityMetadata,
    WarmUpMetadata,
)
from trading_framework.market_analysis.storage import AnalysisResultStore
from trading_framework.time.models.timeframe import Timeframe


def _identity(key_suffix: str = "a") -> ComputationIdentity:
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
    return ComputationIdentity(
        component_id=ComponentId("volatility.atr"),
        component_version=ComponentVersion("1.0.0"),
        implementation_id=ImplementationId("numpy.atr"),
        implementation_version=ImplementationVersion("1.0.0"),
        parameters=CanonicalParameters.from_mapping({"period": 14}),
        dataset_ref=dataset_ref,
        timeframe=Timeframe("1m"),
        requested_range=TimeRange(
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        ),
        dependency_keys=(key_suffix,),
    )


def _result(identity: ComputationIdentity) -> AnalysisResult:
    output_id = OutputId("value")
    schema = OutputSchema(outputs=(OutputFieldSpec(output_id, "float64"),))
    lineage = Lineage(
        dataset_ref=identity.dataset_ref,
        component_id=identity.component_id,
        component_version=identity.component_version,
        implementation_id=identity.implementation_id,
        implementation_version=identity.implementation_version,
        parameters=identity.parameters,
        dependency_keys=identity.dependency_keys,
        engine_version="0.1.0",
        executed_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    return AnalysisResult(
        computation_identity=identity,
        output_schema=schema,
        outputs={output_id: OutputSeries(values=(1.0, 2.0))},
        lineage=lineage,
        validity=ValidityMetadata(valid_from_index=0, valid_to_index=1),
        warmup=WarmUpMetadata(warmup_bars=0, valid_from_index=0, valid_to_index=1),
        availability=AvailabilityMetadata(policy=AvailabilityPolicy.SAME_BAR),
        diagnostics={},
    )


def test_store_put_and_get_by_identity() -> None:
    store = AnalysisResultStore()
    identity = _identity()
    result = _result(identity)
    store.put(result)
    assert store.get(identity) is result


def test_store_deduplicates_by_canonical_identity_key() -> None:
    store = AnalysisResultStore()
    identity = _identity()
    store.put(_result(identity))
    replacement = _result(identity)
    store.put(replacement)
    assert store.get(identity) is replacement
    assert len(store) == 1


def test_lookup_output_by_output_ref() -> None:
    store = AnalysisResultStore()
    identity = _identity()
    result = _result(identity)
    store.put(result)
    series = store.lookup_output(OutputRef(identity, OutputId("value")))
    assert series.values == (1.0, 2.0)


def test_dependency_results_requires_all_keys() -> None:
    store = AnalysisResultStore()
    with pytest.raises(ValidationError, match="missing dependency results"):
        store.dependency_results(["missing-key"])
