"""Computation identity tests."""

from datetime import UTC, datetime

from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis import (
    ComponentId,
    ComponentRequest,
    ComponentVersion,
    ComputationIdentity,
    ImplementationId,
    ImplementationVersion,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
    TimeRange,
)
from trading_framework.time.models.timeframe import Timeframe


def _sample_identity(*, period: int = 14) -> ComputationIdentity:
    schema = ParameterSchema(fields=(ParameterFieldSpec("period", ParameterType.INT, default=14),))
    request = ComponentRequest.from_raw(
        ComponentId("volatility.atr"),
        schema,
        {"period": period},
    )
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
    time_range = TimeRange(
        start=datetime(2024, 1, 1, tzinfo=UTC),
        end=datetime(2024, 1, 2, tzinfo=UTC),
    )
    return ComputationIdentity(
        component_id=request.component_id,
        component_version=ComponentVersion("1.0.0"),
        implementation_id=ImplementationId("numpy.atr"),
        implementation_version=ImplementationVersion("1.0.0"),
        parameters=request.parameters,
        dataset_ref=dataset_ref,
        timeframe=Timeframe("1m"),
        requested_range=time_range,
        dependency_keys=(),
    )


def test_computation_identity_differs_from_request_parameters_only() -> None:
    first = _sample_identity(period=14)
    second = _sample_identity(period=50)
    assert first.canonical_key() != second.canonical_key()


def test_computation_identity_is_hashable_and_stable() -> None:
    identity = _sample_identity()
    assert hash(identity) == hash(identity)
    assert identity.canonical_key() == identity.canonical_key()
