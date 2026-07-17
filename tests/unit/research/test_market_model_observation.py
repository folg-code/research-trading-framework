"""Unit tests for MarketModelObservation materialization."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.research import (
    ObservationMaterializationContext,
    derive_observation_id,
    materialize_market_model_observations,
)
from trading_framework.time.models.timeframe import Timeframe


def _synthetic_frame() -> AnalysisFrame:
    start = datetime(2024, 1, 3, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=index) for index in range(6))
    close = (100.0, 101.0, 102.0, 103.0, 104.0, 105.0)
    return AnalysisFrame(
        timestamps=timestamps,
        columns={"close": close, "high": close, "low": close},
        column_lineage={},
    )


def test_true_edge_materializes_false_to_true_transitions_only() -> None:
    frame = _synthetic_frame()
    timestamps = frame.timestamps
    market_state = pl.DataFrame(
        {
            "timestamp": list(timestamps),
            "available_at": list(timestamps),
            "model_result": [False, True, True, False, True, True],
            "market_model_id": ["high_volatility"] * 6,
        }
    )
    observations = materialize_market_model_observations(
        market_state,
        frame=frame,
        market_view=None,
        context=ObservationMaterializationContext(
            market_model_id="high_volatility",
            instrument="ES.c.0",
            evaluation_timeframe=Timeframe("1m"),
            source_dataset_ref="test-dataset",
        ),
    )
    assert len(observations) == 2
    assert observations["observation_id"].n_unique() == 2
    assert observations["reference_price"].to_list() == [101.0, 104.0]


def test_observation_id_is_stable() -> None:
    detected_at = datetime(2024, 1, 3, 0, 1, tzinfo=UTC)
    first = derive_observation_id(market_model_id="high_volatility", detected_at=detected_at)
    second = derive_observation_id(market_model_id="high_volatility", detected_at=detected_at)
    assert first == second


def test_empty_market_state_returns_empty_observations() -> None:
    frame = _synthetic_frame()
    observations = materialize_market_model_observations(
        pl.DataFrame(
            schema={
                "timestamp": pl.Datetime(time_unit="us", time_zone="UTC"),
                "available_at": pl.Datetime(time_unit="us", time_zone="UTC"),
                "model_result": pl.Boolean(),
                "market_model_id": pl.String(),
            }
        ),
        frame=frame,
        market_view=None,
        context=ObservationMaterializationContext(
            market_model_id="high_volatility",
            instrument="ES.c.0",
            evaluation_timeframe=Timeframe("1m"),
            source_dataset_ref="test-dataset",
        ),
    )
    assert len(observations) == 0


def test_materialize_builds_reference_price_lookup_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from trading_framework.research.observations import market_model_observation as module
    from trading_framework.strategy.reference_price import (
        ReferencePriceLookup,
    )
    from trading_framework.strategy.reference_price import (
        build_reference_price_lookup as real_build,
    )

    frame = _synthetic_frame()
    timestamps = frame.timestamps
    market_state = pl.DataFrame(
        {
            "timestamp": list(timestamps),
            "available_at": list(timestamps),
            "model_result": [False, True, True, False, True, True],
            "market_model_id": ["high_volatility"] * 6,
        }
    )
    call_count = 0

    def counting_build(
        evaluation_frame: AnalysisFrame,
        market_view: AnalysisDataView | None = None,
    ) -> ReferencePriceLookup:
        nonlocal call_count
        call_count += 1
        return real_build(evaluation_frame, market_view)

    monkeypatch.setattr(module, "build_reference_price_lookup", counting_build)

    observations = materialize_market_model_observations(
        market_state,
        frame=frame,
        market_view=None,
        context=ObservationMaterializationContext(
            market_model_id="high_volatility",
            instrument="ES.c.0",
            evaluation_timeframe=Timeframe("1m"),
            source_dataset_ref="test-dataset",
        ),
    )

    assert call_count == 1
    assert observations["reference_price"].to_list() == [101.0, 104.0]
