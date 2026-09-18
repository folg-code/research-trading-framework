"""Tests for conditional context expectancy (Phase 18 18A Milestone 1b / Sprint 069)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

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
from trading_framework.research.analytics.context_expectancy import (
    CONTEXT_EXPECTANCY_SCHEMA_VERSION,
    compute_context_expectancy,
    empty_context_expectancy_dataframe,
    state_context_aliases,
)
from trading_framework.research.simulation.facts import empty_simulated_trades_dataframe

_START = datetime(2024, 1, 1, tzinfo=UTC)
_DATASET_REF = DatasetRef(
    dataset_id=DatasetId(
        instrument_id=Identifier("TEST.INST"),
        data_type="ohlcv",
        timeframe="1m",  # type: ignore[arg-type]
        provider="csv",
        source_id="context-expectancy-test",
    ),
    version=1,
)


def _fake_output_ref(*, component_id: str, output_id: str = "state") -> OutputRef:
    from trading_framework.time.models.timeframe import Timeframe

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


def _trades_frame(rows: list[dict[str, object]]) -> pl.DataFrame:
    if not rows:
        return empty_simulated_trades_dataframe()
    return pl.DataFrame(rows).select(empty_simulated_trades_dataframe().columns)


def _trade_row(*, offset: int, net_pnl: float) -> dict[str, object]:
    at = _START + timedelta(minutes=offset)
    return {
        "trade_id": f"t-{offset}",
        "strategy_model_id": "s",
        "instrument": "TEST",
        "direction": "long",
        "entry_signal_at": at,
        "entry_fill_at": at,
        "entry_fill_price": 10.0,
        "exit_signal_at": at,
        "exit_fill_at": at,
        "exit_fill_price": 10.0,
        "quantity": 1.0,
        "gross_pnl": net_pnl,
        "commission_paid": 0.0,
        "net_pnl": net_pnl,
        "bars_held": 0,
        "exit_reason": "test",
        "source_dataset_ref": "dataset@1",
    }


def test_state_context_aliases_resolves_state_kind_component_only() -> None:
    market_model_def = _market_model_using_volatility_state()
    lineage = {
        "vol_state_alias": _fake_output_ref(component_id="volatility.state"),
        "vol_atr_alias": _fake_output_ref(component_id="volatility.atr", output_id="value"),
    }
    frame = _frame(
        columns={"vol_state_alias": (0.0, 1.0), "vol_atr_alias": (1.2, 1.3)},
        lineage=lineage,
    )
    aliases = state_context_aliases(market_model=market_model_def, frame=frame)
    assert aliases == {"vol_state_alias": "volatility.state"}


def test_state_context_aliases_ignores_components_not_referenced_by_market_model() -> None:
    market_model_def = _market_model_using_volatility_state()
    # A STATE-kind component the market model does NOT reference must not qualify.
    lineage = {"other_state_alias": _fake_output_ref(component_id="volatility.regime_state")}
    frame = _frame(columns={"other_state_alias": (0.0,)}, lineage=lineage)
    aliases = state_context_aliases(market_model=market_model_def, frame=frame)
    assert aliases == {}


def test_compute_context_expectancy_empty_when_no_state_component() -> None:
    market_model_def = _market_model_using_volatility_state()
    frame = _frame(columns={"unrelated": (0.0, 1.0)}, lineage={})
    trades = _trades_frame([_trade_row(offset=0, net_pnl=1.0)])
    result = compute_context_expectancy(
        run_id="r1", market_model=market_model_def, frame=frame, trades=trades
    )
    assert result.height == 0
    assert result.columns == empty_context_expectancy_dataframe().columns


def test_compute_context_expectancy_empty_when_no_trades() -> None:
    market_model_def = _market_model_using_volatility_state()
    lineage = {"vol_state_alias": _fake_output_ref(component_id="volatility.state")}
    frame = _frame(columns={"vol_state_alias": (0.0, 1.0)}, lineage=lineage)
    result = compute_context_expectancy(
        run_id="r1",
        market_model=market_model_def,
        frame=frame,
        trades=empty_simulated_trades_dataframe(),
    )
    assert result.height == 0


def test_compute_context_expectancy_groups_by_label() -> None:
    market_model_def = _market_model_using_volatility_state()
    lineage = {"vol_state_alias": _fake_output_ref(component_id="volatility.state")}
    # bars 0..5: state values 0,0,0,0,0,1 -- trades enter at bars 0,1,2 (label 0.0)
    # and bar 5 (label 1.0).
    frame = _frame(
        columns={"vol_state_alias": (0.0, 0.0, 0.0, 0.0, 0.0, 1.0)},
        lineage=lineage,
    )
    trades = _trades_frame(
        [
            _trade_row(offset=0, net_pnl=10.0),
            _trade_row(offset=1, net_pnl=-4.0),
            _trade_row(offset=2, net_pnl=2.0),
            _trade_row(offset=5, net_pnl=100.0),
        ]
    )
    result = compute_context_expectancy(
        run_id="r1",
        market_model=market_model_def,
        frame=frame,
        trades=trades,
        min_sample_size=2,
        interpretation_min_sample_size=3,
    )
    rows = {row["label"]: row for row in result.to_dicts()}
    assert rows["0.0"]["schema_version"] == CONTEXT_EXPECTANCY_SCHEMA_VERSION
    assert rows["0.0"]["component_id"] == "volatility.state"
    assert rows["0.0"]["sample_count"] == 3
    assert rows["0.0"]["eligible"] is True
    assert rows["0.0"]["interpretable"] is True
    assert rows["0.0"]["net_pnl_mean"] == pytest.approx((10.0 - 4.0 + 2.0) / 3)
    assert rows["0.0"]["win_rate"] == pytest.approx(2 / 3)
    assert rows["1.0"]["sample_count"] == 1
    assert rows["1.0"]["eligible"] is False
    assert rows["1.0"]["net_pnl_mean"] is None


def test_compute_context_expectancy_counts_missing_context() -> None:
    market_model_def = _market_model_using_volatility_state()
    lineage = {"vol_state_alias": _fake_output_ref(component_id="volatility.state")}
    frame = _frame(columns={"vol_state_alias": (0.0, 0.0)}, lineage=lineage)
    trades = _trades_frame(
        [
            _trade_row(offset=0, net_pnl=1.0),
            # offset 99 has no matching frame timestamp -- missing context.
            _trade_row(offset=99, net_pnl=1.0),
        ]
    )
    result = compute_context_expectancy(
        run_id="r1",
        market_model=market_model_def,
        frame=frame,
        trades=trades,
        min_sample_size=1,
    )
    assert result.height == 1
    assert result.to_dicts()[0]["missing_context_count"] == 1
