"""AnalysisWorkspace tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.models import MarketBar
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
    OutputSchema,
    OutputSeries,
    TimeRange,
    ValidityMetadata,
    WarmUpMetadata,
)
from trading_framework.market_analysis.assembly.session_metadata import TradingSessionMetadata
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.storage import AnalysisWorkspace
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver


def _market_view(bar_count: int = 2) -> AnalysisDataView:
    bars = []
    for minute in range(bar_count):
        observed_at = datetime(2024, 1, 1, 12, minute, tzinfo=UTC)
        bars.append(
            MarketBar(
                open=Price(Decimal("100")),
                high=Price(Decimal("105")),
                low=Price(Decimal("99")),
                close=Price(Decimal("103")),
                volume=Volume(1000),
                observed_at=observed_at,
                available_at=observed_at + timedelta(minutes=1),
            )
        )
    return AnalysisDataView.from_bars(bars)


def _result() -> AnalysisResult:
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
    identity = ComputationIdentity(
        component_id=ComponentId("volatility.atr"),
        component_version=ComponentVersion("1.0.0"),
        implementation_id=ImplementationId("numpy.atr"),
        implementation_version=ImplementationVersion("1.0.0"),
        parameters=CanonicalParameters.from_mapping({"period": 14}),
        dataset_ref=dataset_ref,
        computation_timeframe=Timeframe("1m"),
        requested_range=TimeRange(
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        ),
        dependency_keys=(),
    )
    output_id = OutputId("value")
    return AnalysisResult(
        computation_identity=identity,
        output_schema=OutputSchema(outputs=(OutputFieldSpec(output_id, "float64"),)),
        outputs={output_id: OutputSeries(values=(1.0, 2.0))},
        lineage=Lineage(
            dataset_ref=dataset_ref,
            component_id=identity.component_id,
            component_version=identity.component_version,
            implementation_id=identity.implementation_id,
            implementation_version=identity.implementation_version,
            parameters=identity.parameters,
            dependency_keys=(),
            engine_version="0.1.0",
            executed_at=datetime(2024, 1, 1, tzinfo=UTC),
        ),
        validity=ValidityMetadata(valid_from_index=0, valid_to_index=1),
        warmup=WarmUpMetadata(warmup_bars=0, valid_from_index=0, valid_to_index=1),
        availability=AvailabilityMetadata(policy=AvailabilityPolicy.SAME_BAR),
        diagnostics={},
    )


def test_workspace_registers_results_via_executor_owned_api() -> None:
    workspace = AnalysisWorkspace(_market_view())
    result = _result()
    workspace.register(result)
    assert len(workspace.result_store) == 1


def test_workspace_view_exposes_market_and_dependencies() -> None:
    workspace = AnalysisWorkspace(_market_view())
    result = _result()
    workspace.register(result)
    view = workspace.view_for((result.computation_identity.canonical_key(),))
    assert len(view.market) == 2
    assert view.dependency_results[result.computation_identity.canonical_key()] is result
    assert view.session_metadata is None


def test_workspace_view_requires_registered_dependencies() -> None:
    workspace = AnalysisWorkspace(_market_view())
    with pytest.raises(ValidationError, match="missing dependency results"):
        workspace.view_for(("missing",))


def test_workspace_view_passes_evaluation_grid_session_metadata() -> None:
    market = _market_view(3)
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(market.timestamps, resolver)
    workspace = AnalysisWorkspace(market, session_metadata=metadata, session_resolver=resolver)
    view = workspace.view_for(())
    assert view.session_metadata is metadata


def test_workspace_view_reresolves_session_metadata_on_resampled_grid() -> None:
    from trading_framework.market_analysis.data.resample import resample_analysis_view
    from trading_framework.market_analysis.models.resample import ResampleSpec

    bars = []
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    for minute in range(10):
        observed_at = start + timedelta(minutes=minute)
        bars.append(
            MarketBar(
                open=Price(Decimal("100")),
                high=Price(Decimal("105")),
                low=Price(Decimal("99")),
                close=Price(Decimal("103")),
                volume=Volume(1000),
                observed_at=observed_at,
                available_at=observed_at + timedelta(minutes=1),
            )
        )
    source = AnalysisDataView.from_bars(bars)
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(source.timestamps, resolver)
    workspace = AnalysisWorkspace(source, session_metadata=metadata, session_resolver=resolver)
    resampled = resample_analysis_view(source, ResampleSpec(target_timeframe=Timeframe("5m")))
    workspace.register_resampled_view("5m", resampled)
    view = workspace.view_for((), input_identity_key="5m")
    assert view.session_metadata is not None
    assert len(view.session_metadata) == len(resampled)
    assert len(view.session_metadata) != len(source)
    assert view.session_metadata is not metadata
    again = workspace.view_for((), input_identity_key="5m")
    assert again.session_metadata is view.session_metadata
