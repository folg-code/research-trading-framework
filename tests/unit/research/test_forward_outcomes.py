"""Tests for forward outcome definition and calculator (S008 T004-T005)."""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.research.outcomes import (
    ForwardOutcomeDefinition,
    OutcomeStatus,
    compute_forward_outcomes,
    compute_forward_outcomes_for_horizons,
    empty_forward_outcomes_dataframe,
)
from trading_framework.signal_model.definitions import SignalDirection


def _occurrence_row(
    *,
    occurrence_id: str = "occ-1",
    detected_at: datetime,
    direction: str = SignalDirection.LONG.value,
    reference_price: float = 100.0,
) -> dict[str, object]:
    return {
        "occurrence_id": occurrence_id,
        "signal_model_id": "test_signal",
        "detected_at": detected_at,
        "available_at": detected_at,
        "direction": direction,
        "reference_price": reference_price,
        "instrument": "TEST",
        "evaluation_timeframe": "1m",
        "source_dataset_ref": "test@1",
    }


def _flat_ohlcv(
    close: tuple[float, ...],
) -> dict[str, tuple[float, ...]]:
    return {
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": close,
    }


def test_forward_outcome_definition_rejects_non_positive_horizon() -> None:
    with pytest.raises(ValidationError, match="horizon_bars"):
        ForwardOutcomeDefinition(horizon_bars=0)


def test_empty_forward_outcomes_has_canonical_schema() -> None:
    frame = empty_forward_outcomes_dataframe()
    assert frame.columns == [
        "occurrence_id",
        "horizon_bars",
        "outcome_status",
        "terminal_price",
        "forward_return",
        "mfe",
        "mae",
    ]
    assert len(frame) == 0


def test_horizon_excludes_signal_bar(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    """Signal at t=2, horizon=3 → terminal close index 5."""
    start = datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=index) for index in range(10))
    close = (100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0)
    frame = build_test_frame(columns={"close": close, "high": close, "low": close}, start=start)
    frame = AnalysisFrame(
        timestamps=timestamps,
        columns={"close": close, "high": close, "low": close},
        column_lineage={},
    )
    occurrences = pl.DataFrame([_occurrence_row(detected_at=timestamps[2], reference_price=102.0)])
    outcomes = compute_forward_outcomes(
        occurrences,
        frame=frame,
        ohlcv=_flat_ohlcv(close),
        definition=ForwardOutcomeDefinition(horizon_bars=3),
    )
    row = outcomes.row(0, named=True)
    assert row["outcome_status"] == OutcomeStatus.COMPLETE.value
    assert row["terminal_price"] == 105.0
    assert row["forward_return"] == pytest.approx(105.0 / 102.0 - 1.0)


def test_incomplete_horizon_emits_status_with_null_metrics() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=index) for index in range(6))
    close = (100.0, 101.0, 102.0, 103.0, 104.0, 105.0)
    frame = AnalysisFrame(
        timestamps=timestamps,
        columns={"close": close, "high": close, "low": close},
        column_lineage={},
    )
    occurrences = pl.DataFrame([_occurrence_row(detected_at=timestamps[4], reference_price=104.0)])
    outcomes = compute_forward_outcomes(
        occurrences,
        frame=frame,
        ohlcv=_flat_ohlcv(close),
        definition=ForwardOutcomeDefinition(horizon_bars=5),
    )
    row = outcomes.row(0, named=True)
    assert row["outcome_status"] == OutcomeStatus.INCOMPLETE_HORIZON.value
    assert row["terminal_price"] is None
    assert row["forward_return"] is None
    assert row["mfe"] is None
    assert row["mae"] is None


def test_insufficient_data_when_reference_price_is_nan() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = (start, start + timedelta(minutes=1))
    close = (100.0, 101.0)
    frame = AnalysisFrame(
        timestamps=timestamps,
        columns={"close": close, "high": close, "low": close},
        column_lineage={},
    )
    occurrences = pl.DataFrame(
        [_occurrence_row(detected_at=timestamps[0], reference_price=math.nan)]
    )
    outcomes = compute_forward_outcomes(
        occurrences,
        frame=frame,
        ohlcv=_flat_ohlcv(close),
        definition=ForwardOutcomeDefinition(horizon_bars=1),
    )
    assert outcomes.row(0, named=True)["outcome_status"] == OutcomeStatus.INSUFFICIENT_DATA.value


def test_insufficient_data_when_window_contains_nan() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=index) for index in range(4))
    close = (100.0, math.nan, 102.0, 103.0)
    highs = close
    lows = close
    frame = AnalysisFrame(
        timestamps=timestamps,
        columns={"close": close, "high": highs, "low": lows},
        column_lineage={},
    )
    occurrences = pl.DataFrame([_occurrence_row(detected_at=timestamps[0], reference_price=100.0)])
    outcomes = compute_forward_outcomes(
        occurrences,
        frame=frame,
        ohlcv={"open": close, "high": highs, "low": lows, "close": close, "volume": close},
        definition=ForwardOutcomeDefinition(horizon_bars=2),
    )
    assert outcomes.row(0, named=True)["outcome_status"] == OutcomeStatus.INSUFFICIENT_DATA.value


def test_short_direction_inverts_signed_return() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=index) for index in range(4))
    close = (100.0, 100.0, 90.0, 90.0)
    frame = AnalysisFrame(
        timestamps=timestamps,
        columns={"close": close, "high": close, "low": close},
        column_lineage={},
    )
    occurrences = pl.DataFrame(
        [
            _occurrence_row(
                detected_at=timestamps[0],
                direction=SignalDirection.SHORT.value,
                reference_price=100.0,
            )
        ]
    )
    outcomes = compute_forward_outcomes(
        occurrences,
        frame=frame,
        ohlcv=_flat_ohlcv(close),
        definition=ForwardOutcomeDefinition(horizon_bars=2),
    )
    row = outcomes.row(0, named=True)
    assert row["forward_return"] == pytest.approx(0.1)


def test_mfe_non_negative_and_mae_non_positive() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=index) for index in range(5))
    close = (100.0, 101.0, 99.0, 102.0, 103.0)
    highs = (100.0, 103.0, 101.0, 104.0, 105.0)
    lows = (100.0, 100.0, 98.0, 101.0, 102.0)
    frame = AnalysisFrame(
        timestamps=timestamps,
        columns={"close": close, "high": highs, "low": lows},
        column_lineage={},
    )
    occurrences = pl.DataFrame([_occurrence_row(detected_at=timestamps[0], reference_price=100.0)])
    outcomes = compute_forward_outcomes(
        occurrences,
        frame=frame,
        ohlcv={"open": close, "high": highs, "low": lows, "close": close, "volume": close},
        definition=ForwardOutcomeDefinition(horizon_bars=4),
    )
    row = outcomes.row(0, named=True)
    assert row["mfe"] >= 0.0
    assert row["mae"] <= 0.0


def test_multi_horizon_long_format() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=index) for index in range(12))
    close = tuple(100.0 + index for index in range(12))
    frame = AnalysisFrame(
        timestamps=timestamps,
        columns={"close": close, "high": close, "low": close},
        column_lineage={},
    )
    occurrences = pl.DataFrame(
        [
            _occurrence_row(occurrence_id="a", detected_at=timestamps[0]),
            _occurrence_row(occurrence_id="b", detected_at=timestamps[1]),
        ]
    )
    outcomes = compute_forward_outcomes_for_horizons(
        occurrences,
        frame=frame,
        ohlcv=_flat_ohlcv(close),
        horizons=(3, 5),
    )
    assert len(outcomes) == 4
    assert set(outcomes["horizon_bars"].to_list()) == {3, 5}


def test_short_mfe_mae_use_inverted_excursions() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=index) for index in range(5))
    close = (100.0, 100.0, 100.0, 100.0, 100.0)
    highs = (100.0, 105.0, 104.0, 103.0, 102.0)
    lows = (100.0, 99.0, 98.0, 97.0, 96.0)
    frame = AnalysisFrame(
        timestamps=timestamps,
        columns={"close": close, "high": highs, "low": lows},
        column_lineage={},
    )
    occurrences = pl.DataFrame(
        [
            _occurrence_row(
                detected_at=timestamps[0],
                direction=SignalDirection.SHORT.value,
                reference_price=100.0,
            )
        ]
    )
    outcomes = compute_forward_outcomes(
        occurrences,
        frame=frame,
        ohlcv={"open": close, "high": highs, "low": lows, "close": close, "volume": close},
        definition=ForwardOutcomeDefinition(horizon_bars=4),
    )
    row = outcomes.row(0, named=True)
    # Short: favorable from lows (down to 96 → +0.04), adverse from highs (up to 105 → -0.05)
    assert row["mfe"] == pytest.approx(0.04)
    assert row["mae"] == pytest.approx(-0.05)
