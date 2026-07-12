"""Integration tests for Sprint 010 Signal Research analytics."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

import pytest

from trading_framework.application.model_evaluation.canonical_examples import (
    build_canonical_market_model_high_volatility,
    build_canonical_signal_higher_low_on_event,
)
from trading_framework.application.signal_research import (
    AnalyzeSignalResearchRequest,
    RunSignalResearchRequest,
    analyze_signal_research_run,
    run_signal_research,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.research import ResearchScope
from trading_framework.research.analytics import (
    GroupDimension,
    validate_conditional_comparison,
    validate_grouped_summaries,
    validate_run_summaries,
)
from trading_framework.research.datasets import RunDatasetRef
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

_FIXTURE_VOLATILITY_THRESHOLD = 0.5
_HORIZON = 5


def _write_published_dataset(storage_root: Path, *, csv_path: Path, source_id: str) -> DatasetRef:
    from trading_framework.application.market_data import (
        ImportExternalDatasetRequest,
        finalize_dataset,
        import_external_dataset,
        publish_dataset,
    )
    from trading_framework.market.normalization import OhlcvColumnMapping, OhlcvImportConfig
    from trading_framework.market.temporal import BarTimestampSemantics

    dataset_id = DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id=source_id,
    )
    result = import_external_dataset(
        ImportExternalDatasetRequest(
            path=csv_path,
            dataset_id=dataset_id,
            import_config=OhlcvImportConfig(
                column_mapping=OhlcvColumnMapping(
                    timestamp="timestamp",
                    open="open",
                    high="high",
                    low="low",
                    close="close",
                    volume="volume",
                ),
                timeframe=Timeframe("1m"),
                timestamp_semantics=BarTimestampSemantics.INTERVAL_START,
                source_timezone=UTC,
            ),
            schema_version="ohlcv.v1",
            normalization_version="utc-interval-start.v1",
        ),
        storage_root=storage_root,
    )
    finalize_dataset(result.dataset_ref, storage_root=storage_root)
    publish_dataset(result.dataset_ref, storage_root=storage_root)
    metadata = FileDatasetRegistry(storage_root).get(result.dataset_ref)
    assert metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED
    return result.dataset_ref


def _run_scope(
    *,
    storage_root: Path,
    dataset_ref: DatasetRef,
    requested_range: TimeRange,
    scope: ResearchScope,
) -> str:
    market_model = build_canonical_market_model_high_volatility(
        threshold=_FIXTURE_VOLATILITY_THRESHOLD
    )
    signal_model = build_canonical_signal_higher_low_on_event()
    if scope is ResearchScope.SIGNAL_MODEL_ONLY:
        request = RunSignalResearchRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=requested_range,
            storage_root=storage_root,
            signal_models=(signal_model,),
            horizons=(_HORIZON,),
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
        )
    elif scope is ResearchScope.MARKET_MODEL_ONLY:
        request = RunSignalResearchRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=requested_range,
            storage_root=storage_root,
            scope=scope,
            market_models=(market_model,),
            signal_models=(),
            horizons=(_HORIZON,),
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
        )
    else:
        request = RunSignalResearchRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=requested_range,
            storage_root=storage_root,
            scope=ResearchScope.MARKET_AND_SIGNAL,
            market_models=(market_model,),
            signal_models=(signal_model,),
            horizons=(_HORIZON,),
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
        )
    result = run_signal_research(request)
    return result.run_ref.run_id


@pytest.mark.parametrize(
    "scope", [ResearchScope.SIGNAL_MODEL_ONLY, ResearchScope.MARKET_MODEL_ONLY]
)
def test_analyze_signal_research_run_summary_for_v1_and_market_only(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
    scope: ResearchScope,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(
        storage_root,
        csv_path=ohlcv_sample_1m_path,
        source_id=f"s010-analytics-{scope.value}",
    )
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    run_id = _run_scope(
        storage_root=storage_root,
        dataset_ref=dataset_ref,
        requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
        scope=scope,
    )

    result = analyze_signal_research_run(
        AnalyzeSignalResearchRequest(
            run_ref=RunDatasetRef(run_id=run_id),
            storage_root=storage_root,
            horizons=(_HORIZON,),
        )
    )

    validate_run_summaries(result.run_summaries)
    summary = result.run_summaries.row(0, named=True)
    assert summary["sample_size_complete"] > 0
    assert summary["metrics_eligible"] is True
    assert result.metadata.research_scope == scope.value
    assert result.grouped_summaries is None
    assert result.conditional_comparison is None


def test_analyze_signal_research_run_market_and_signal_grouping_and_conditional(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(
        storage_root,
        csv_path=ohlcv_sample_1m_path,
        source_id="s010-analytics-combined",
    )
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    run_id = _run_scope(
        storage_root=storage_root,
        dataset_ref=dataset_ref,
        requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
        scope=ResearchScope.MARKET_AND_SIGNAL,
    )

    result = analyze_signal_research_run(
        AnalyzeSignalResearchRequest(
            run_ref=RunDatasetRef(run_id=run_id),
            storage_root=storage_root,
            horizons=(_HORIZON,),
            group_by=(GroupDimension.RTH_MEMBERSHIP, GroupDimension.TIME_OF_DAY),
            conditional_context=True,
        )
    )

    validate_run_summaries(result.run_summaries)
    assert result.grouped_summaries is not None
    validate_grouped_summaries(result.grouped_summaries)
    assert result.grouped_summaries.height >= 2

    assert result.conditional_comparison is not None
    validate_conditional_comparison(result.conditional_comparison)
    conditional = result.conditional_comparison.row(0, named=True)
    assert conditional["context_false_sample_size"] > 0
    assert (
        conditional["context_true_sample_size"] + conditional["context_false_sample_size"]
        == result.run_summaries.row(0, named=True)["sample_size_complete"]
    )
