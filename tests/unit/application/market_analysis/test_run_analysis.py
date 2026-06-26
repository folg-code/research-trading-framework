"""Tests for run_analysis application workflow."""

from datetime import UTC
from pathlib import Path

from trading_framework.application.market_analysis.run_analysis import (
    RunAnalysisRequest,
    run_analysis,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.market_analysis import (
    AnalysisFrameColumnSpec,
    AnalysisFrameRequest,
    ComponentId,
    ComponentRequest,
    OutputId,
    TimeRange,
)
from trading_framework.market_analysis.components.trend import EmaComponent
from trading_framework.market_analysis.components.volatility import (
    AtrComponent,
    TrueRangeComponent,
    VolatilityStateComponent,
)
from trading_framework.time.models.timeframe import Timeframe


def _write_published_dataset(storage_root: Path, *, csv_path: Path) -> DatasetRef:
    from trading_framework.application.market_data import (
        ImportExternalDatasetRequest,
        finalize_dataset,
        import_external_dataset,
        publish_dataset,
    )
    from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
    from trading_framework.market.normalization import OhlcvColumnMapping, OhlcvImportConfig
    from trading_framework.market.temporal import BarTimestampSemantics

    dataset_id = DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="run-analysis",
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


def test_run_analysis_executes_vertical_slice(
    tmp_path: Path,
    market_data_fixtures_dir: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(
        storage_root,
        csv_path=market_data_fixtures_dir / "sample_ohlcv.csv",
    )
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    state_params = VolatilityStateComponent().parameter_schema.canonicalize(
        {"period": 2, "threshold": 1.0}
    )
    ema_params = EmaComponent().parameter_schema.canonicalize({"period": 2})
    result = run_analysis(
        RunAnalysisRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            storage_root=storage_root,
            component_requests=(
                ComponentRequest(
                    component_id=ComponentId("volatility.state"),
                    parameters=state_params,
                ),
                ComponentRequest(
                    component_id=ComponentId("trend.ema"),
                    parameters=ema_params,
                ),
            ),
            frame_request=AnalysisFrameRequest(
                analysis_columns=(
                    AnalysisFrameColumnSpec(
                        component_id=ComponentId("volatility.true_range"),
                        parameters=TrueRangeComponent().parameter_schema.canonicalize({}),
                        output_id=OutputId("value"),
                        alias="true_range",
                    ),
                    AnalysisFrameColumnSpec(
                        component_id=ComponentId("volatility.atr"),
                        parameters=AtrComponent().parameter_schema.canonicalize({"period": 2}),
                        output_id=OutputId("value"),
                        alias="atr",
                    ),
                    AnalysisFrameColumnSpec(
                        component_id=ComponentId("trend.ema"),
                        parameters=ema_params,
                        output_id=OutputId("value"),
                        alias="ema",
                    ),
                    AnalysisFrameColumnSpec(
                        component_id=ComponentId("volatility.state"),
                        parameters=state_params,
                        output_id=OutputId("state"),
                        alias="volatility_state",
                    ),
                    AnalysisFrameColumnSpec(
                        component_id=ComponentId("volatility.state"),
                        parameters=state_params,
                        output_id=OutputId("distance_to_threshold"),
                        alias="volatility_distance",
                    ),
                )
            ),
        )
    )
    assert len(result.plan.nodes) >= 4
    assert result.frame is not None
    assert "close" in result.frame.columns
    assert "true_range" in result.frame.columns
    assert "atr" in result.frame.columns
    assert "ema" in result.frame.columns
    assert "volatility_state" in result.frame.columns
    assert "volatility_distance" in result.frame.columns
