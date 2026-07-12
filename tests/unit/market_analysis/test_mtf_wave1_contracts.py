"""Sprint 004 Wave 1 — MTF request, identity and resample contracts."""

from datetime import UTC, datetime

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis import (
    ComponentId,
    ComponentVersion,
    ComputationIdentity,
    ImplementationId,
    ImplementationVersion,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
)
from trading_framework.market_analysis.identity.mtf import AlignmentIdentity, ResampleIdentity
from trading_framework.market_analysis.models.alignment import AlignmentPolicy
from trading_framework.market_analysis.models.context import AnalysisContext
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.market_analysis.models.request import ComponentRequest
from trading_framework.market_analysis.models.resample import ResampleSpec
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.market_analysis.planning.resolution import RequestResolver
from trading_framework.time.models.timeframe import Timeframe


def _dataset_ref() -> DatasetRef:
    return DatasetRef(
        DatasetId(
            instrument_id=Identifier("NQ.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id="sample",
        ),
        version=1,
    )


def _time_range() -> TimeRange:
    return TimeRange(
        start=datetime(2024, 1, 1, tzinfo=UTC),
        end=datetime(2024, 1, 2, tzinfo=UTC),
    )


def test_component_request_defaults_computation_to_source() -> None:
    request = ComponentRequest(
        component_id=ComponentId("volatility.atr"),
        parameters=CanonicalParameters.from_mapping({"period": 14}),
    )
    assert request.resolved_computation_timeframe(source_timeframe=Timeframe("1m")) == Timeframe(
        "1m"
    )


def test_component_request_rejects_finer_computation_timeframe() -> None:
    schema = ParameterSchema(fields=(ParameterFieldSpec("period", ParameterType.INT, default=14),))
    request = ComponentRequest.from_raw(
        ComponentId("volatility.atr"),
        schema,
        {"period": 14},
        computation_timeframe=Timeframe("1m"),
    )
    with pytest.raises(ValidationError, match="computation_timeframe"):
        request.resolved_computation_timeframe(source_timeframe=Timeframe("5m"))


def test_analysis_context_supports_evaluation_timeframe_default() -> None:
    context = AnalysisContext(
        dataset_ref=_dataset_ref(),
        timeframe=Timeframe("1m"),
        requested_range=_time_range(),
        computation_range=_time_range(),
        engine_version="0.1.0",
    )
    assert context.source_timeframe == Timeframe("1m")
    assert context.evaluation_timeframe == Timeframe("1m")


def test_analysis_context_rejects_coarser_evaluation_timeframe() -> None:
    with pytest.raises(ValidationError, match="evaluation_timeframe"):
        AnalysisContext(
            dataset_ref=_dataset_ref(),
            timeframe=Timeframe("1m"),
            evaluation_timeframe=Timeframe("5m"),
            requested_range=_time_range(),
            computation_range=_time_range(),
            engine_version="0.1.0",
        )


def test_request_resolver_materializes_timeframe_roles() -> None:
    schema = ParameterSchema(fields=(ParameterFieldSpec("period", ParameterType.INT, default=14),))
    request = ComponentRequest.from_raw(
        ComponentId("volatility.atr"),
        schema,
        {"period": 14},
        computation_timeframe=Timeframe("5m"),
    )
    run_context = RequestResolver.run_context(
        source_timeframe=Timeframe("1m"),
        evaluation_timeframe=Timeframe("1m"),
    )
    resolved = RequestResolver.resolve_component(
        component_id=ComponentId("volatility.atr"),
        request=request,
        run_context=run_context,
    )
    assert resolved.source_timeframe == Timeframe("1m")
    assert resolved.computation_timeframe == Timeframe("5m")
    assert resolved.evaluation_timeframe == Timeframe("1m")


def test_computation_identity_stable_for_same_computation_inputs() -> None:
    params = ParameterSchema(
        fields=(ParameterFieldSpec("period", ParameterType.INT, default=14),)
    ).canonicalize({"period": 14})
    first = ComputationIdentity(
        component_id=ComponentId("volatility.atr"),
        component_version=ComponentVersion("1.0.0"),
        implementation_id=ImplementationId("numpy.atr"),
        implementation_version=ImplementationVersion("1.0.0"),
        parameters=params,
        dataset_ref=_dataset_ref(),
        computation_timeframe=Timeframe("5m"),
        requested_range=_time_range(),
        dependency_keys=("resample:abc",),
    )
    second = ComputationIdentity(
        component_id=ComponentId("volatility.atr"),
        component_version=ComponentVersion("1.0.0"),
        implementation_id=ImplementationId("numpy.atr"),
        implementation_version=ImplementationVersion("1.0.0"),
        parameters=params,
        dataset_ref=_dataset_ref(),
        computation_timeframe=Timeframe("5m"),
        requested_range=_time_range(),
        dependency_keys=("resample:abc",),
    )
    assert first.canonical_key() == second.canonical_key()


def test_alignment_identity_differs_by_policy_not_computation() -> None:
    computation_key = ComputationIdentity(
        component_id=ComponentId("volatility.atr"),
        component_version=ComponentVersion("1.0.0"),
        implementation_id=ImplementationId("numpy.atr"),
        implementation_version=ImplementationVersion("1.0.0"),
        parameters=CanonicalParameters.from_mapping({"period": 14}),
        dataset_ref=_dataset_ref(),
        computation_timeframe=Timeframe("5m"),
        requested_range=_time_range(),
        dependency_keys=(),
    ).canonical_key()
    time_range = _time_range()
    last_closed = AlignmentIdentity(
        component_computation_key=computation_key,
        output_id="value",
        evaluation_timeframe=Timeframe("1m"),
        evaluation_range=time_range,
        alignment_policy=AlignmentPolicy.LAST_CLOSED_BAR,
    )
    intrabar = AlignmentIdentity(
        component_computation_key=computation_key,
        output_id="value",
        evaluation_timeframe=Timeframe("1m"),
        evaluation_range=time_range,
        alignment_policy=AlignmentPolicy.INTRABAR,
    )
    assert last_closed.canonical_key() != intrabar.canonical_key()


def test_resample_identity_is_stable() -> None:
    identity = ResampleIdentity(
        dataset_ref=_dataset_ref(),
        source_timeframe=Timeframe("1m"),
        target_timeframe=Timeframe("5m"),
        resample_spec=ResampleSpec(target_timeframe=Timeframe("5m")),
        requested_range=_time_range(),
    )
    duplicate = ResampleIdentity(
        dataset_ref=_dataset_ref(),
        source_timeframe=Timeframe("1m"),
        target_timeframe=Timeframe("5m"),
        resample_spec=ResampleSpec(target_timeframe=Timeframe("5m")),
        requested_range=_time_range(),
    )
    assert identity.canonical_key() == duplicate.canonical_key()


def test_resample_spec_rejects_non_utc_timezone() -> None:
    with pytest.raises(ValidationError, match="UTC"):
        ResampleSpec(target_timeframe=Timeframe("5m"), timezone="US/Eastern")
