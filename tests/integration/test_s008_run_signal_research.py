"""Integration tests for run_signal_research end-to-end workflow."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

from trading_framework.application.model_evaluation.canonical_examples import (
    build_canonical_signal_higher_low_on_event,
)
from trading_framework.application.signal_research import (
    RunSignalResearchRequest,
    run_signal_research,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.research.datasets import SignalResearchDatasetRepository
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
        source_id="s008-run-signal-research",
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


def test_run_signal_research_persists_and_reloads_round_trip(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    signal_model = build_canonical_signal_higher_low_on_event()
    horizons = (5, 10)

    result = run_signal_research(
        RunSignalResearchRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            storage_root=storage_root,
            signal_models=(signal_model,),
            horizons=horizons,
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
        )
    )

    assert result.run_id == result.manifest.run_id
    assert len(result.occurrences) > 0
    assert len(result.outcomes) == len(result.occurrences) * len(horizons)

    repository = SignalResearchDatasetRepository(storage_root)
    loaded = repository.read(result.run_ref)
    assert loaded.manifest.run_id == result.run_id
    assert loaded.occurrences.sort("occurrence_id").equals(result.occurrences.sort("occurrence_id"))
    assert loaded.outcomes.sort(["occurrence_id", "horizon_bars"]).equals(
        result.outcomes.sort(["occurrence_id", "horizon_bars"])
    )


def test_run_signal_research_is_deterministic_for_same_inputs(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    signal_model = build_canonical_signal_higher_low_on_event()
    request = RunSignalResearchRequest(
        dataset_ref=dataset_ref,
        timeframe=Timeframe("1m"),
        requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
        storage_root=storage_root,
        signal_models=(signal_model,),
        horizons=(5,),
        evaluation_timeframe=Timeframe("1m"),
        session_resolver=CmeEsRthSessionResolver(),
        persist=False,
    )

    first = run_signal_research(request)
    second = run_signal_research(request)
    assert first.run_id == second.run_id


def test_run_signal_research_refuses_duplicate_persist(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    signal_model = build_canonical_signal_higher_low_on_event()
    request = RunSignalResearchRequest(
        dataset_ref=dataset_ref,
        timeframe=Timeframe("1m"),
        requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
        storage_root=storage_root,
        signal_models=(signal_model,),
        horizons=(5,),
        evaluation_timeframe=Timeframe("1m"),
        session_resolver=CmeEsRthSessionResolver(),
        persist=True,
    )

    run_signal_research(request)
    try:
        run_signal_research(request)
        duplicate_failed = False
    except FileExistsError:
        duplicate_failed = True
    assert duplicate_failed
