"""Authored momentum.stochastic_* references evaluate on the fixture harness path."""

from datetime import UTC
from pathlib import Path

from trading_framework.application.model_evaluation import EvaluateModelsRequest, evaluate_models
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.model_authoring import market_model, momentum
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
        source_id="s051-momentum-stochastic-dsl",
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


def test_stochastic_k_returns_operand_usable_in_a_condition() -> None:
    operand = momentum.stochastic_k(period=14, smoothing_period=3)
    assert isinstance(operand, Operand)
    condition = operand > 0.0
    assert condition is not None


def test_stochastic_d_returns_operand() -> None:
    assert isinstance(momentum.stochastic_d(), Operand)


def test_authored_stochastic_k_evaluates_on_fixture(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    stochastic_low = market_model(
        "stochastic_low",
        when=(momentum.stochastic_k(period=5, smoothing_period=3) >= 0.0),
    )

    result = evaluate_models(
        EvaluateModelsRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            storage_root=storage_root,
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
            market_models=(stochastic_low.definition,),
        )
    )

    assert result.analysis.frame is not None
    assert "stochastic_low" in result.market_model_results
    computed_ids = {
        analysis_result.computation_identity.component_id.value
        for analysis_result in result.analysis.workspace.result_store.results().values()
    }
    assert "momentum.stochastic" in computed_ids
    frame = result.market_model_results["stochastic_low"]
    assert frame.height > 0
    assert frame["market_model_id"][0] == "stochastic_low"
