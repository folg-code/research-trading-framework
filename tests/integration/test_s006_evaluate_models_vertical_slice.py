"""S006-T021 — end-to-end evaluate_models vertical slice with canonical examples."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

import polars as pl

from trading_framework.application.model_evaluation import EvaluateModelsRequest, evaluate_models
from trading_framework.application.model_evaluation.canonical_examples import (
    CANONICAL_COMBINED_SIGNAL_ID,
    CANONICAL_MARKET_MODEL_ID,
    CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID,
    CANONICAL_SIGNAL_HIGHER_LOW_ID,
    build_canonical_model_bundle,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.market_analysis import TimeRange
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
        source_id="s006-vertical-slice",
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


def _assert_dense_model_result(frame: pl.DataFrame, *, model_id: str) -> None:
    assert frame.columns == [
        "timestamp",
        "available_at",
        "model_result",
        "market_model_id",
    ]
    assert frame["market_model_id"].unique().to_list() == [model_id]
    assert len(frame) >= 100
    assert frame["available_at"].null_count() == 0


def _assert_dense_condition_result(frame: pl.DataFrame, *, signal_id: str) -> None:
    assert frame.columns == [
        "timestamp",
        "available_at",
        "condition_met",
        "signal_model_id",
    ]
    assert frame["signal_model_id"].unique().to_list() == [signal_id]
    assert len(frame) >= 100
    assert frame["available_at"].null_count() == 0


def test_s006_vertical_slice_canonical_examples(
    tmp_path: Path,
    market_data_fixtures_dir: Path,
) -> None:
    storage_root = tmp_path / "storage"
    fixture = market_data_fixtures_dir / "s005_swing_vertical_slice_1m.csv"
    dataset_ref = _write_published_dataset(storage_root, csv_path=fixture)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    bundle = build_canonical_model_bundle()

    result = evaluate_models(
        EvaluateModelsRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            storage_root=storage_root,
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
            market_models=bundle.market_models,
            signal_models=bundle.signal_models,
        )
    )

    assert result.analysis.frame is not None
    assert len(result.analysis.frame.timestamps) >= 100

    _assert_dense_model_result(
        result.market_model_results[CANONICAL_MARKET_MODEL_ID],
        model_id=CANONICAL_MARKET_MODEL_ID,
    )
    _assert_dense_condition_result(
        result.signal_model_conditions[CANONICAL_SIGNAL_HIGHER_LOW_ID],
        signal_id=CANONICAL_SIGNAL_HIGHER_LOW_ID,
    )
    _assert_dense_condition_result(
        result.signal_model_conditions[CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID],
        signal_id=CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID,
    )
    _assert_dense_condition_result(
        result.signal_model_conditions[CANONICAL_COMBINED_SIGNAL_ID],
        signal_id=CANONICAL_COMBINED_SIGNAL_ID,
    )

    higher_low_emissions = result.signal_model_emissions[CANONICAL_SIGNAL_HIGHER_LOW_ID]
    assert higher_low_emissions.columns == [
        "detected_at",
        "available_at",
        "signal_model_id",
        "direction",
        "firing_policy",
    ]
    if len(higher_low_emissions) > 0:
        assert higher_low_emissions["firing_policy"].unique().to_list() == ["on_event"]

    edge_emissions = result.signal_model_emissions[CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID]
    if len(edge_emissions) > 0:
        assert edge_emissions["firing_policy"].unique().to_list() == ["on_true_edge"]
    assert len(edge_emissions) <= len(
        result.signal_model_conditions[CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID]
    )

    combined_emissions = result.signal_model_emissions[CANONICAL_COMBINED_SIGNAL_ID]
    assert len(combined_emissions) <= len(
        result.signal_model_conditions[CANONICAL_COMBINED_SIGNAL_ID]
    )
    if len(combined_emissions) > 0:
        assert combined_emissions["direction"].unique().to_list() == ["long"]

    volatility_results = [
        analysis_result
        for analysis_result in result.analysis.workspace.result_store.results().values()
        if analysis_result.computation_identity.component_id.value == "volatility.state"
    ]
    swing_results = [
        analysis_result
        for analysis_result in result.analysis.workspace.result_store.results().values()
        if analysis_result.computation_identity.component_id.value == "structure.swing"
    ]
    assert len(volatility_results) == 1
    assert len(swing_results) == 1
