"""Authored trend.ema_distance models evaluate on the fixture harness path."""

from datetime import UTC
from pathlib import Path

from trading_framework.application.model_evaluation import EvaluateModelsRequest, evaluate_models
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.model_authoring import market_model, trend
from trading_framework.model_authoring.references.operand import Operand
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
        source_id="s048-ema-distance-dsl",
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


def test_ema_distance_returns_operand_usable_in_a_condition() -> None:
    operand = trend.ema_distance(period=20, atr_period=14, timeframe=None)
    assert isinstance(operand, Operand)
    condition = operand > 1.5
    assert condition is not None


def test_authored_ema_distance_evaluates_on_fixture(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    stretched_above_ema = market_model(
        "stretched_above_ema",
        when=(trend.ema_distance(period=20, atr_period=14) > -100.0),
    )

    result = evaluate_models(
        EvaluateModelsRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            storage_root=storage_root,
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
            market_models=(stretched_above_ema.definition,),
        )
    )

    assert result.analysis.frame is not None
    assert "stretched_above_ema" in result.market_model_results
    computed_ids = {
        analysis_result.computation_identity.component_id.value
        for analysis_result in result.analysis.workspace.result_store.results().values()
    }
    assert "trend.ema_distance" in computed_ids
    assert "trend.ema" in computed_ids
    assert "volatility.atr" in computed_ids
    frame = result.market_model_results["stretched_above_ema"]
    assert frame.height > 0
    assert frame["market_model_id"][0] == "stretched_above_ema"
