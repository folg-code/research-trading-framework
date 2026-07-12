"""S005-T013 — end-to-end run_analysis vertical slice with session, MTF swing and frame."""

from __future__ import annotations

import math
from datetime import UTC
from pathlib import Path

from trading_framework.application.market_analysis.run_analysis import (
    AnalysisRunResult,
    RunAnalysisRequest,
    run_analysis,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
)
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
from trading_framework.market_analysis.components.structure import SwingStructureComponent
from trading_framework.market_analysis.components.trend import EmaComponent
from trading_framework.market_analysis.components.volatility import AtrComponent
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

PIVOT_RANGE = 15


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
        source_id="s005-swing-vertical-slice",
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


def _run_s005_analysis(
    *,
    storage_root: Path,
    dataset_ref: DatasetRef,
    metadata: DatasetMetadata,
    pivot_range: int,
) -> AnalysisRunResult:
    swing_schema = SwingStructureComponent().parameter_schema
    swing_params = swing_schema.canonicalize({"pivot_range": pivot_range})
    indicator_schema = ParameterSchema(
        fields=(ParameterFieldSpec("period", ParameterType.INT, default=3),)
    )
    atr_params = AtrComponent().parameter_schema.canonicalize({"period": 3})
    ema_params = EmaComponent().parameter_schema.canonicalize({"period": 3})

    swing_request = ComponentRequest.from_raw(
        ComponentId("structure.swing"),
        swing_schema,
        {"pivot_range": pivot_range},
        computation_timeframe=Timeframe("5m"),
    )
    atr_request = ComponentRequest.from_raw(
        ComponentId("volatility.atr"),
        indicator_schema,
        {"period": 3},
        computation_timeframe=Timeframe("5m"),
    )
    ema_request = ComponentRequest(
        component_id=ComponentId("trend.ema"),
        parameters=ema_params,
    )

    return run_analysis(
        RunAnalysisRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            storage_root=storage_root,
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
            component_requests=(swing_request, atr_request, ema_request),
            frame_request=AnalysisFrameRequest(
                market_fields=("close",),
                analysis_columns=(
                    AnalysisFrameColumnSpec(
                        component_id=ComponentId("structure.swing"),
                        parameters=swing_params,
                        output_id=OutputId("swing_high_event"),
                        alias="swing_high_event_5m",
                    ),
                    AnalysisFrameColumnSpec(
                        component_id=ComponentId("structure.swing"),
                        parameters=swing_params,
                        output_id=OutputId("latest_swing_high_level"),
                        alias="latest_swing_high_level_5m",
                    ),
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


def test_s005_vertical_slice_session_mtf_swing_and_frame(
    tmp_path: Path,
    market_data_fixtures_dir: Path,
) -> None:
    storage_root = tmp_path / "storage"
    fixture = market_data_fixtures_dir / "s005_swing_vertical_slice_1m.csv"
    dataset_ref = _write_published_dataset(storage_root, csv_path=fixture)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)

    result = _run_s005_analysis(
        storage_root=storage_root,
        dataset_ref=dataset_ref,
        metadata=metadata,
        pivot_range=PIVOT_RANGE,
    )

    swing_result = next(
        analysis_result
        for analysis_result in result.workspace.result_store.results().values()
        if analysis_result.computation_identity.component_id == ComponentId("structure.swing")
    )
    assert swing_result.availability.delay_bars == PIVOT_RANGE
    assert swing_result.warmup.warmup_bars == PIVOT_RANGE

    assert result.frame is not None
    frame = result.frame
    bar_count = len(frame.timestamps)
    assert bar_count >= 100
    assert frame.session_metadata is not None
    assert len(frame.session_metadata) == bar_count
    assert all(
        session_id in {"ES_RTH", "OUTSIDE_RTH"} for session_id in frame.session_metadata.session_ids
    )
    assert any(frame.session_metadata.is_rth)
    assert not all(frame.session_metadata.is_rth)

    events = frame.columns["swing_high_event_5m"]
    state = frame.columns["latest_swing_high_level_5m"]
    assert sum(value == 1.0 for value in events) >= 1
    for index in range(1, len(events)):
        if events[index] == 1.0:
            assert events[index - 1] != 1.0

    first_state = next(index for index, value in enumerate(state) if not math.isnan(value))
    if first_state + 1 < len(state):
        assert state[first_state + 1] == state[first_state]

    assert not math.isnan(frame.columns["ema_1m"][3])
    assert math.isnan(frame.columns["atr_5m"][0])
    assert len(result.plan.resample_keys()) == 1
