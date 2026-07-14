"""Unit tests for run_strategy_research orchestration."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path
from unittest.mock import patch

from trading_framework.application.market_data.query_historical import (
    query_historical as real_query_historical,
)
from trading_framework.application.strategy_research import (
    RunStrategyResearchRequest,
    run_strategy_research,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.research.simulation import SimulationAssumptions
from trading_framework.strategy import build_canonical_strategy_model
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver


def _write_published_dataset(storage_root: Path, *, csv_path: Path) -> DatasetRef:
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
        source_id="unit-run-strategy-research",
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


def test_run_strategy_research_queries_historical_bars_once(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    strategy_model = build_canonical_strategy_model()
    query_count = 0

    def counting_query_historical(*args, **kwargs):
        nonlocal query_count
        query_count += 1
        return real_query_historical(*args, **kwargs)

    with (
        patch(
            "trading_framework.application.strategy_research.run_strategy_research.query_historical",
            side_effect=counting_query_historical,
        ),
        patch(
            "trading_framework.application.market_analysis.load_data_view.query_historical",
            side_effect=counting_query_historical,
        ),
    ):
        result = run_strategy_research(
            RunStrategyResearchRequest(
                dataset_ref=dataset_ref,
                timeframe=Timeframe("1m"),
                requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
                storage_root=storage_root,
                strategy_model=strategy_model,
                assumptions=SimulationAssumptions(),
                evaluation_timeframe=Timeframe("1m"),
                session_resolver=CmeEsRthSessionResolver(),
                persist=False,
            )
        )

    assert query_count == 1
    assert len(result.equity) > 0


def test_run_strategy_research_records_subphase_timings_when_timer_active(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    from io import StringIO

    from trading_framework.infrastructure.observability.phase_timer import PhaseTimer
    from trading_framework.infrastructure.observability.profile_context import phase_timer_context

    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    strategy_model = build_canonical_strategy_model()
    timer = PhaseTimer(enabled=True, log_stream=StringIO())

    with phase_timer_context(timer):
        timer.begin_session()
        run_strategy_research(
            RunStrategyResearchRequest(
                dataset_ref=dataset_ref,
                timeframe=Timeframe("1m"),
                requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
                storage_root=storage_root,
                strategy_model=strategy_model,
                assumptions=SimulationAssumptions(),
                evaluation_timeframe=Timeframe("1m"),
                session_resolver=CmeEsRthSessionResolver(),
                persist=False,
            )
        )

    assert "strategy_research.evaluate_models" in timer._stats
    assert "strategy_research.load_ohlcv" in timer._stats
    assert "strategy_research.simulate" in timer._stats
    assert "evaluate_models.run_analysis" in timer._stats
    assert "run_analysis.assemble_frame" in timer._stats
    assert "ohlcv.query_bars" in timer._stats
    assert timer._stats["strategy_research.evaluate_models"].call_count == 1
