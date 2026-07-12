"""Integration test for the Market Analysis MTF vertical slice (S004-T013).

Fixture provenance: ``tests/fixtures/market_data/mtf_vertical_slice_1m.csv`` — ninety
1m OHLCV rows imported through the same CSV pipeline as the single-TF vertical slice.
"""

from __future__ import annotations

import math
from datetime import UTC
from pathlib import Path

from trading_framework.application.market_analysis.run_analysis import (
    RunAnalysisRequest,
    run_analysis,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.market.temporal.bar_interval import derive_bar_interval
from trading_framework.market_analysis import (
    AnalysisFrameColumnSpec,
    AnalysisFrameRequest,
    ComponentId,
    ComponentRequest,
    OutputId,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
    TimeRange,
)
from trading_framework.market_analysis.components.trend import EmaComponent
from trading_framework.market_analysis.components.volatility import AtrComponent
from trading_framework.time.models.timeframe import Timeframe


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
        source_id="mtf-vertical-slice",
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
            lineage={"source_file": csv_path.name},
        ),
        storage_root=storage_root,
    )
    finalize_dataset(result.dataset_ref, storage_root=storage_root)
    publish_dataset(result.dataset_ref, storage_root=storage_root)
    metadata = FileDatasetRegistry(storage_root).get(result.dataset_ref)
    assert metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED
    return result.dataset_ref


def test_mtf_vertical_slice_aligns_5m_atr_to_1m_with_1m_ema(
    tmp_path: Path,
    market_data_fixtures_dir: Path,
) -> None:
    storage_root = tmp_path / "storage"
    fixture = market_data_fixtures_dir / "mtf_vertical_slice_1m.csv"
    dataset_ref = _write_published_dataset(storage_root, csv_path=fixture)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)

    schema = ParameterSchema(fields=(ParameterFieldSpec("period", ParameterType.INT, default=3),))
    atr_params = AtrComponent().parameter_schema.canonicalize({"period": 3})
    ema_params = EmaComponent().parameter_schema.canonicalize({"period": 3})
    atr_request = ComponentRequest.from_raw(
        ComponentId("volatility.atr"),
        schema,
        {"period": 3},
        computation_timeframe=Timeframe("5m"),
    )
    ema_request = ComponentRequest(
        component_id=ComponentId("trend.ema"),
        parameters=ema_params,
    )

    result = run_analysis(
        RunAnalysisRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            storage_root=storage_root,
            evaluation_timeframe=Timeframe("1m"),
            component_requests=(atr_request, ema_request),
            frame_request=AnalysisFrameRequest(
                market_fields=("close",),
                analysis_columns=(
                    AnalysisFrameColumnSpec(
                        component_id=ComponentId("volatility.atr"),
                        parameters=atr_params,
                        output_id=OutputId("value"),
                        alias="atr_5m",
                    ),
                    AnalysisFrameColumnSpec(
                        component_id=ComponentId("trend.ema"),
                        parameters=ema_params,
                        output_id=OutputId("value"),
                        alias="ema_1m",
                    ),
                ),
            ),
        )
    )

    assert result.frame is not None
    frame = result.frame
    assert len(frame.timestamps) == 90
    for column in ("close", "atr_5m", "ema_1m"):
        assert column in frame.columns
        assert len(frame.columns[column]) == 90

    assert not math.isnan(frame.columns["ema_1m"][3])
    assert math.isnan(frame.columns["atr_5m"][0])

    eval_at = frame.timestamps[37]
    atr_value_at_eval = frame.columns["atr_5m"][37]
    assert not math.isnan(atr_value_at_eval)
    incomplete_htf_available = derive_bar_interval(
        frame.timestamps[35],
        Timeframe("5m"),
    )[1]
    assert incomplete_htf_available > eval_at

    assert len(result.plan.resample_keys()) == 1
