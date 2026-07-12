"""Integration tests for evaluate_models orchestration."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

from trading_framework.application.model_evaluation import EvaluateModelsRequest, evaluate_models
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.market_analysis import OutputId, TimeRange
from trading_framework.market_analysis.components.structure import SwingStructureComponent
from trading_framework.market_analysis.components.volatility import VolatilityStateComponent
from trading_framework.market_model import MarketModelDefinition
from trading_framework.model_expression import (
    CompareExpression,
    ComparisonOperator,
    ComponentOutputReference,
)
from trading_framework.signal_model import (
    SignalDirection,
    SignalFiringPolicy,
    SignalModelDefinition,
)
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
        source_id="s006-evaluate-models",
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


def test_evaluate_models_runs_analysis_once_for_shared_dependencies(
    tmp_path: Path,
    market_data_fixtures_dir: Path,
) -> None:
    storage_root = tmp_path / "storage"
    fixture = market_data_fixtures_dir / "s005_swing_vertical_slice_1m.csv"
    dataset_ref = _write_published_dataset(storage_root, csv_path=fixture)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)

    volatility_component = VolatilityStateComponent()
    swing_component = SwingStructureComponent()
    volatility_reference = ComponentOutputReference(
        component_id=volatility_component.component_id,
        parameters=volatility_component.parameter_schema.canonicalize(
            {"period": 14, "threshold": 5.0}
        ),
        output_id=OutputId("state"),
    )
    swing_reference = ComponentOutputReference(
        component_id=swing_component.component_id,
        parameters=swing_component.parameter_schema.canonicalize({"pivot_range": 15}),
        output_id=OutputId("higher_low_event"),
        computation_timeframe=Timeframe("5m"),
    )
    shared_market_model = MarketModelDefinition(
        market_model_id="high_volatility",
        expression=CompareExpression(
            operand=volatility_reference,
            operator=ComparisonOperator.EQ,
            value=1.0,
        ),
    )
    duplicate_market_model = MarketModelDefinition(
        market_model_id="not_low_volatility",
        expression=CompareExpression(
            operand=volatility_reference,
            operator=ComparisonOperator.NE,
            value=0.0,
        ),
    )
    signal_model = SignalModelDefinition(
        signal_model_id="higher_low_long",
        expression=CompareExpression(
            operand=swing_reference,
            operator=ComparisonOperator.EQ,
            value=True,
        ),
        direction=SignalDirection.LONG,
        firing_policy=SignalFiringPolicy.ON_EVENT,
    )

    result = evaluate_models(
        EvaluateModelsRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            storage_root=storage_root,
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
            market_models=(shared_market_model, duplicate_market_model),
            signal_models=(signal_model,),
        )
    )

    assert result.analysis.frame is not None
    assert len(result.market_model_results) == 2
    assert len(result.signal_model_conditions) == 1
    assert len(result.signal_model_emissions) == 1

    high_volatility = result.market_model_results["high_volatility"]
    assert high_volatility.columns == [
        "timestamp",
        "available_at",
        "model_result",
        "market_model_id",
    ]
    assert high_volatility["market_model_id"][0] == "high_volatility"

    emissions = result.signal_model_emissions["higher_low_long"]
    assert emissions.columns == [
        "detected_at",
        "available_at",
        "signal_model_id",
        "direction",
        "firing_policy",
    ]
    assert emissions["signal_model_id"][0] == "higher_low_long"
    assert emissions["direction"][0] == "long"
    assert emissions["firing_policy"][0] == "on_event"

    volatility_results = [
        analysis_result
        for analysis_result in result.analysis.workspace.result_store.results().values()
        if analysis_result.computation_identity.component_id.value == "volatility.state"
    ]
    assert len(volatility_results) == 1
