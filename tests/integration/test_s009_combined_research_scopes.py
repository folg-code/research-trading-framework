"""Integration tests for Sprint 009 combined research scopes."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

import polars as pl

from trading_framework.application.model_evaluation.canonical_examples import (
    CANONICAL_MARKET_MODEL_ID,
    CANONICAL_SIGNAL_HIGHER_LOW_ID,
    build_canonical_market_model_high_volatility,
    build_canonical_signal_higher_low_on_event,
)
from trading_framework.application.signal_research import (
    RunSignalResearchRequest,
    run_signal_research,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.paths import signal_research_run_dir
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.research import (
    SIGNAL_RESEARCH_SCHEMA_V2,
    ResearchScope,
)
from trading_framework.research.datasets import SignalResearchDatasetRepository
from trading_framework.signal_model.definitions import SignalModelDefinition
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

# Fixture-calibrated threshold — canonical 5.0 yields no HIGH volatility on ohlcv_sample_1m.
_FIXTURE_VOLATILITY_THRESHOLD = 0.5


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


def _base_request(
    *,
    dataset_ref: DatasetRef,
    storage_root: Path,
    requested_range: TimeRange,
    scope: ResearchScope,
    horizons: tuple[int, ...],
    market_models: tuple[MarketModelDefinition, ...] = (),
    signal_models: tuple[SignalModelDefinition, ...] = (),
    persist: bool = True,
) -> RunSignalResearchRequest:
    return RunSignalResearchRequest(
        dataset_ref=dataset_ref,
        timeframe=Timeframe("1m"),
        requested_range=requested_range,
        storage_root=storage_root,
        scope=scope,
        market_models=market_models,
        signal_models=signal_models,
        horizons=horizons,
        evaluation_timeframe=Timeframe("1m"),
        session_resolver=CmeEsRthSessionResolver(),
        persist=persist,
    )


def test_run_signal_research_market_and_signal_persists_v2_envelope(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(
        storage_root,
        csv_path=ohlcv_sample_1m_path,
        source_id="s009-market-and-signal",
    )
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    market_model = build_canonical_market_model_high_volatility(
        threshold=_FIXTURE_VOLATILITY_THRESHOLD,
    )
    signal_model = build_canonical_signal_higher_low_on_event()
    horizons = (5, 10)

    result = run_signal_research(
        _base_request(
            dataset_ref=dataset_ref,
            storage_root=storage_root,
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            scope=ResearchScope.MARKET_AND_SIGNAL,
            market_models=(market_model,),
            signal_models=(signal_model,),
            horizons=horizons,
        )
    )

    assert result.manifest.schema_version == SIGNAL_RESEARCH_SCHEMA_V2
    assert result.manifest.research_scope is ResearchScope.MARKET_AND_SIGNAL
    assert result.manifest.market_model_ids == (CANONICAL_MARKET_MODEL_ID,)
    assert result.manifest.signal_model_ids == (CANONICAL_SIGNAL_HIGHER_LOW_ID,)
    assert len(result.occurrences) > 0
    assert len(result.context) == len(result.occurrences)
    assert len(result.observations) == 0
    assert len(result.outcomes) == len(result.occurrences) * len(horizons)

    run_dir = signal_research_run_dir(storage_root, result.run_id)
    assert (run_dir / "occurrences.parquet").exists()
    assert (run_dir / "context.parquet").exists()
    assert not (run_dir / "observations.parquet").exists()

    repository = SignalResearchDatasetRepository(storage_root)
    loaded = repository.read(result.run_ref)
    assert loaded.manifest.run_id == result.run_id
    assert loaded.context.sort("occurrence_id").equals(result.context.sort("occurrence_id"))
    assert loaded.occurrences.sort("occurrence_id").equals(result.occurrences.sort("occurrence_id"))
    assert loaded.outcomes.sort(["occurrence_id", "horizon_bars"]).equals(
        result.outcomes.sort(["occurrence_id", "horizon_bars"])
    )


def test_market_and_signal_context_alignment_contract(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(
        storage_root,
        csv_path=ohlcv_sample_1m_path,
        source_id="s009-context-contract",
    )
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    market_model = build_canonical_market_model_high_volatility(
        threshold=_FIXTURE_VOLATILITY_THRESHOLD,
    )
    signal_model = build_canonical_signal_higher_low_on_event()

    result = run_signal_research(
        _base_request(
            dataset_ref=dataset_ref,
            storage_root=storage_root,
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            scope=ResearchScope.MARKET_AND_SIGNAL,
            market_models=(market_model,),
            signal_models=(signal_model,),
            horizons=(5,),
            persist=False,
        )
    )

    assert len(result.context) == len(result.occurrences)
    joined = result.occurrences.join(result.context, on="occurrence_id", how="inner")
    assert len(joined) == len(result.occurrences)
    assert joined["context_evaluated_at"].equals(joined["available_at"])

    false_rows = result.context.filter(~pl.col("context_met_at_available_at")).height
    assert false_rows > 0


def test_three_scopes_produce_distinct_envelopes(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(
        storage_root,
        csv_path=ohlcv_sample_1m_path,
        source_id="s009-three-scopes",
    )
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    requested_range = TimeRange(start=metadata.start_at, end=metadata.end_at)
    market_model = build_canonical_market_model_high_volatility(
        threshold=_FIXTURE_VOLATILITY_THRESHOLD,
    )
    signal_model = build_canonical_signal_higher_low_on_event()
    horizons = (5,)

    signal_only = run_signal_research(
        _base_request(
            dataset_ref=dataset_ref,
            storage_root=storage_root,
            requested_range=requested_range,
            scope=ResearchScope.SIGNAL_MODEL_ONLY,
            signal_models=(signal_model,),
            horizons=horizons,
        )
    )
    market_only = run_signal_research(
        _base_request(
            dataset_ref=dataset_ref,
            storage_root=storage_root,
            requested_range=requested_range,
            scope=ResearchScope.MARKET_MODEL_ONLY,
            market_models=(market_model,),
            horizons=horizons,
        )
    )
    combined = run_signal_research(
        _base_request(
            dataset_ref=dataset_ref,
            storage_root=storage_root,
            requested_range=requested_range,
            scope=ResearchScope.MARKET_AND_SIGNAL,
            market_models=(market_model,),
            signal_models=(signal_model,),
            horizons=horizons,
        )
    )

    assert signal_only.run_id != market_only.run_id != combined.run_id
    assert signal_only.manifest.research_scope is None
    assert market_only.manifest.research_scope is ResearchScope.MARKET_MODEL_ONLY
    assert combined.manifest.research_scope is ResearchScope.MARKET_AND_SIGNAL

    signal_dir = signal_research_run_dir(storage_root, signal_only.run_id)
    market_dir = signal_research_run_dir(storage_root, market_only.run_id)
    combined_dir = signal_research_run_dir(storage_root, combined.run_id)

    assert (signal_dir / "occurrences.parquet").exists()
    assert not (signal_dir / "observations.parquet").exists()
    assert not (signal_dir / "context.parquet").exists()

    assert (market_dir / "observations.parquet").exists()
    assert not (market_dir / "occurrences.parquet").exists()
    assert not (market_dir / "context.parquet").exists()

    assert (combined_dir / "occurrences.parquet").exists()
    assert (combined_dir / "context.parquet").exists()
    assert not (combined_dir / "observations.parquet").exists()
