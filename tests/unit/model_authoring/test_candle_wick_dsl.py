"""Authored candle.wick models evaluate on the fixture harness path."""

from datetime import UTC
from pathlib import Path

from trading_framework.application.model_evaluation import EvaluateModelsRequest, evaluate_models
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.model_authoring import candle, market_model
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
        source_id="s047-candle-wick-dsl",
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


def test_authored_candle_wick_evaluates_on_fixture(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    upper_wick_dominant = market_model(
        "upper_wick_dominant",
        when=(candle.upper_wick_ratio() > candle.body_ratio()),
    )

    result = evaluate_models(
        EvaluateModelsRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            storage_root=storage_root,
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
            market_models=(upper_wick_dominant.definition,),
        )
    )

    assert result.analysis.frame is not None
    assert "upper_wick_dominant" in result.market_model_results
    computed_ids = {
        analysis_result.computation_identity.component_id.value
        for analysis_result in result.analysis.workspace.result_store.results().values()
    }
    assert "candle.wick" in computed_ids
    frame = result.market_model_results["upper_wick_dominant"]
    assert frame.height > 0
    assert frame["market_model_id"][0] == "upper_wick_dominant"
