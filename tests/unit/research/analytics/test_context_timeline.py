"""Tests for context timeline / persistence (Phase 18 18B Milestone 1 / Sprint 073)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.market_analysis.identity.component import (
    ComponentId,
    ComponentVersion,
    ImplementationId,
    ImplementationVersion,
)
from trading_framework.market_analysis.identity.computation import ComputationIdentity
from trading_framework.market_analysis.models.output_ref import OutputRef
from trading_framework.market_analysis.models.outputs import OutputId
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.model_authoring import market_model
from trading_framework.model_authoring import volatility as authoring_volatility
from trading_framework.research.analytics.context_timeline import (
    CONTEXT_PERSISTENCE_SCHEMA_VERSION,
    CONTEXT_TIMELINE_SCHEMA_VERSION,
    compute_context_persistence,
    compute_context_timeline,
    empty_context_persistence_dataframe,
    empty_context_timeline_dataframe,
)
from trading_framework.time.models.timeframe import Timeframe

_START = datetime(2024, 1, 1, tzinfo=UTC)
_DATASET_REF = DatasetRef(
    dataset_id=DatasetId(
        instrument_id=Identifier("TEST.INST"),
        data_type="ohlcv",
        timeframe="1m",  # type: ignore[arg-type]
        provider="csv",
        source_id="context-timeline-test",
    ),
    version=1,
)


def _fake_output_ref(*, component_id: str, output_id: str = "state") -> OutputRef:
    return OutputRef(
        computation_identity=ComputationIdentity(
            component_id=ComponentId(component_id),
            component_version=ComponentVersion("1.0.0"),
            implementation_id=ImplementationId(f"numpy.{component_id.replace('.', '_')}"),
            implementation_version=ImplementationVersion("1.0.0"),
            parameters=CanonicalParameters.from_mapping({}),
            dataset_ref=_DATASET_REF,
            computation_timeframe=Timeframe("1m"),
            requested_range=TimeRange(start=_START, end=_START + timedelta(days=1)),
            dependency_keys=(),
        ),
        output_id=OutputId(output_id),
    )


def _frame(
    *, columns: dict[str, tuple[float, ...]], lineage: dict[str, OutputRef]
) -> AnalysisFrame:
    length = len(next(iter(columns.values())))
    timestamps = tuple(_START + timedelta(minutes=i) for i in range(length))
    return AnalysisFrame(timestamps=timestamps, columns=columns, column_lineage=lineage)


def _market_model_using_volatility_state() -> MarketModelDefinition:
    return market_model(
        "test-market-state",
        when=(authoring_volatility.state(period=14, threshold=5.0) == 1),
    ).definition


def test_compute_context_timeline_empty_when_no_state_component() -> None:
    market_model_def = _market_model_using_volatility_state()
    frame = _frame(columns={"unrelated": (0.0, 1.0)}, lineage={})
    result = compute_context_timeline(run_id="r1", market_model=market_model_def, frame=frame)
    assert result.height == 0
    assert result.columns == empty_context_timeline_dataframe().columns


def test_compute_context_timeline_returns_full_dated_series() -> None:
    market_model_def = _market_model_using_volatility_state()
    lineage = {"vol_state_alias": _fake_output_ref(component_id="volatility.state")}
    frame = _frame(columns={"vol_state_alias": (0.0, 0.0, 1.0)}, lineage=lineage)

    result = compute_context_timeline(run_id="r1", market_model=market_model_def, frame=frame)

    assert result.height == 3
    rows = result.to_dicts()
    assert rows[0]["schema_version"] == CONTEXT_TIMELINE_SCHEMA_VERSION
    assert rows[0]["run_id"] == "r1"
    assert rows[0]["component_id"] == "volatility.state"
    assert [r["label"] for r in rows] == ["0.0", "0.0", "1.0"]


def test_compute_context_persistence_empty_when_no_state_component() -> None:
    market_model_def = _market_model_using_volatility_state()
    frame = _frame(columns={"unrelated": (0.0, 1.0)}, lineage={})
    result = compute_context_persistence(run_id="r1", market_model=market_model_def, frame=frame)
    assert result.height == 0
    assert result.columns == empty_context_persistence_dataframe().columns


def test_compute_context_persistence_run_length_encodes_label_changes() -> None:
    market_model_def = _market_model_using_volatility_state()
    lineage = {"vol_state_alias": _fake_output_ref(component_id="volatility.state")}
    # labels: 0,0,0,1,1,0 -> three runs: [0]x3, [1]x2, [0]x1 (open at end)
    frame = _frame(columns={"vol_state_alias": (0.0, 0.0, 0.0, 1.0, 1.0, 0.0)}, lineage=lineage)

    result = compute_context_persistence(run_id="r1", market_model=market_model_def, frame=frame)

    assert result.height == 3
    rows = result.to_dicts()
    assert rows[0]["schema_version"] == CONTEXT_PERSISTENCE_SCHEMA_VERSION
    assert rows[0]["label"] == "0.0"
    assert rows[0]["duration_bars"] == 3
    assert rows[0]["end_at"] is not None
    assert rows[1]["label"] == "1.0"
    assert rows[1]["duration_bars"] == 2
    assert rows[2]["label"] == "0.0"
    assert rows[2]["duration_bars"] == 1
    assert rows[2]["end_at"] is None  # still open at series end


def test_compute_context_persistence_single_run_when_label_never_changes() -> None:
    market_model_def = _market_model_using_volatility_state()
    lineage = {"vol_state_alias": _fake_output_ref(component_id="volatility.state")}
    frame = _frame(columns={"vol_state_alias": (1.0, 1.0, 1.0)}, lineage=lineage)

    result = compute_context_persistence(run_id="r1", market_model=market_model_def, frame=frame)

    assert result.height == 1
    row = result.to_dicts()[0]
    assert row["duration_bars"] == 3
    assert row["end_at"] is None
