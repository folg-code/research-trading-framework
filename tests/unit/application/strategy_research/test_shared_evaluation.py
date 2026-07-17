"""Tests for shared Strategy Research evaluation context."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from trading_framework.application.strategy_research import (
    RunStrategyResearchRequest,
    SharedStrategyEvaluationCache,
    build_shared_strategy_evaluation_context,
    run_strategy_research,
)
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.research.simulation import SimulationAssumptions
from trading_framework.strategy import build_canonical_strategy_model
from trading_framework.strategy.exit_model import FixedBarsExitModel
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver


def _write_published_dataset(storage_root: Path, *, csv_path: Path) -> DatasetRef:
    from datetime import UTC

    from trading_framework.application.market_data import (
        ImportExternalDatasetRequest,
        finalize_dataset,
        import_external_dataset,
        publish_dataset,
    )
    from trading_framework.core.identifiers import Identifier
    from trading_framework.market.datasets import DatasetId, DatasetLifecycleState
    from trading_framework.market.normalization import OhlcvColumnMapping, OhlcvImportConfig
    from trading_framework.market.temporal import BarTimestampSemantics

    dataset_id = DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="unit-shared-evaluation",
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


def test_shared_evaluation_reuses_ohlcv_load_across_exit_variants(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    from trading_framework.application.market_data.query_historical import (
        query_historical_columnar as real_query,
    )

    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    requested_range = TimeRange(start=metadata.start_at, end=metadata.end_at)
    base = build_canonical_strategy_model()
    query_count = 0

    def counting_query(*args: object, **kwargs: object) -> object:
        nonlocal query_count
        query_count += 1
        return real_query(*args, **kwargs)  # type: ignore[arg-type]

    with (
        patch(
            "trading_framework.application.strategy_research.shared_evaluation.query_historical_columnar",
            side_effect=counting_query,
        ),
        patch(
            "trading_framework.application.strategy_research.run_strategy_research.query_historical_columnar",
            side_effect=counting_query,
        ),
        patch(
            "trading_framework.application.market_analysis.load_data_view.query_historical_columnar",
            side_effect=counting_query,
        ),
    ):
        cache = SharedStrategyEvaluationCache()
        for exit_after_bars in (3, 5, 8):
            strategy_model = replace(
                base,
                exit_model=FixedBarsExitModel(exit_after_bars=exit_after_bars),
            )
            shared = cache.get_or_build(
                dataset_ref=dataset_ref,
                timeframe=Timeframe("1m"),
                requested_range=requested_range,
                storage_root=storage_root,
                strategy_model=strategy_model,
                evaluation_timeframe=Timeframe("1m"),
                session_resolver=CmeEsRthSessionResolver(),
            )
            run_strategy_research(
                RunStrategyResearchRequest(
                    dataset_ref=dataset_ref,
                    timeframe=Timeframe("1m"),
                    requested_range=requested_range,
                    storage_root=storage_root,
                    strategy_model=strategy_model,
                    assumptions=SimulationAssumptions(),
                    evaluation_timeframe=Timeframe("1m"),
                    session_resolver=CmeEsRthSessionResolver(),
                    persist=False,
                    shared_evaluation=shared,
                )
            )

    assert query_count == 1


def test_build_shared_strategy_evaluation_context_matches_canonical_models(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    strategy_model = build_canonical_strategy_model()
    context = build_shared_strategy_evaluation_context(
        dataset_ref=dataset_ref,
        timeframe=Timeframe("1m"),
        requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
        storage_root=storage_root,
        market_model=strategy_model.market_model,
        signal_model=strategy_model.signal_model,
        evaluation_timeframe=Timeframe("1m"),
        session_resolver=CmeEsRthSessionResolver(),
    )
    assert context.matches_strategy_models(strategy_model)
    assert strategy_model.market_model.market_model_id in context.evaluation.market_model_results
