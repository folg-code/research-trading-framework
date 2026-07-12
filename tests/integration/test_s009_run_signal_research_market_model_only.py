"""Integration tests for MARKET_MODEL_ONLY Signal Research workflow."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

from trading_framework.application.model_evaluation.canonical_examples import (
    CANONICAL_MARKET_MODEL_ID,
    build_canonical_market_model_high_volatility,
)
from trading_framework.application.signal_research import (
    RunSignalResearchRequest,
    run_signal_research,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.research import (
    SIGNAL_RESEARCH_SCHEMA_V2,
    ResearchScope,
)
from trading_framework.research.datasets import SignalResearchDatasetRepository
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

# Fixture-calibrated threshold — canonical 5.0 yields no HIGH volatility on ohlcv_sample_1m.
_FIXTURE_VOLATILITY_THRESHOLD = 0.5


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
        source_id="s009-market-model-only",
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


def test_run_signal_research_market_model_only_persists_v2_envelope(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    market_model = build_canonical_market_model_high_volatility(
        threshold=_FIXTURE_VOLATILITY_THRESHOLD,
    )
    horizons = (5, 10)

    result = run_signal_research(
        RunSignalResearchRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            storage_root=storage_root,
            scope=ResearchScope.MARKET_MODEL_ONLY,
            market_models=(market_model,),
            signal_models=(),
            horizons=horizons,
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
        )
    )

    assert result.manifest.schema_version == SIGNAL_RESEARCH_SCHEMA_V2
    assert result.manifest.research_scope is ResearchScope.MARKET_MODEL_ONLY
    assert result.manifest.market_model_ids == (CANONICAL_MARKET_MODEL_ID,)
    assert len(result.observations) > 0
    assert len(result.occurrences) == 0
    assert len(result.outcomes) == len(result.observations) * len(horizons)

    repository = SignalResearchDatasetRepository(storage_root)
    loaded = repository.read(result.run_ref)
    assert loaded.manifest.run_id == result.run_id
    assert loaded.observations.sort("observation_id").equals(
        result.observations.sort("observation_id")
    )
    assert loaded.outcomes.sort(["occurrence_id", "horizon_bars"]).equals(
        result.outcomes.sort(["occurrence_id", "horizon_bars"])
    )
