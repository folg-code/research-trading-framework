"""Tests for Signal Research inspection helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import polars as pl
import pytest

from tests.spike._signal_research_inspection import (
    bars_to_window,
    build_inspection_selection,
    excursion_price_levels,
    query_window_range,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketBar
from trading_framework.research.outcomes.definition import OutcomeStatus


def _bar(at: datetime, close: float) -> MarketBar:
    price = Price(Decimal(str(close)))
    available_at = at + timedelta(minutes=1)
    return MarketBar(
        open=price,
        high=price,
        low=price,
        close=price,
        volume=Volume(1000),
        observed_at=at,
        available_at=available_at,
    )


def test_build_inspection_selection_joins_occurrence_and_outcome() -> None:
    detected_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    occurrences = pl.DataFrame(
        {
            "occurrence_id": ["occ-1"],
            "signal_model_id": ["signal_a"],
            "detected_at": [detected_at],
            "available_at": [detected_at],
            "direction": ["long"],
            "reference_price": [100.0],
            "instrument": ["TEST"],
            "evaluation_timeframe": ["1m"],
            "source_dataset_ref": ["test@1"],
        }
    )
    outcomes = pl.DataFrame(
        {
            "occurrence_id": ["occ-1"],
            "horizon_bars": [3],
            "outcome_status": [OutcomeStatus.COMPLETE.value],
            "terminal_price": [105.0],
            "forward_return": [0.05],
            "mfe": [0.06],
            "mae": [-0.01],
        }
    )

    selection = build_inspection_selection(
        occurrences,
        outcomes,
        occurrence_index=0,
        horizon_bars=3,
    )
    assert selection.occurrence_id == "occ-1"
    assert selection.forward_return == pytest.approx(0.05)
    assert selection.terminal_price == pytest.approx(105.0)


def test_bars_to_window_finds_horizon_end_index() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    bars = [_bar(start + timedelta(minutes=index), 100.0 + index) for index in range(8)]
    detected_at = bars[2].observed_at

    window = bars_to_window(
        bars,
        detected_at=detected_at,
        horizon_bars=3,
        padding_bars=1,
    )

    assert window.signal_index == 1
    assert window.horizon_end_index == 4
    assert window.horizon_end_timestamp == bars[5].observed_at


def test_query_window_range_expands_padding() -> None:
    detected_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    start, end = query_window_range(
        detected_at=detected_at,
        horizon_bars=5,
        padding_bars=2,
        bar_step=timedelta(minutes=1),
    )
    assert start == detected_at - timedelta(minutes=2)
    assert end == detected_at + timedelta(minutes=7)


def test_excursion_price_levels_for_long() -> None:
    mfe, mae = excursion_price_levels(
        reference_price=100.0,
        direction="long",
        mfe=0.05,
        mae=-0.02,
    )
    assert mfe == pytest.approx(105.0)
    assert mae == pytest.approx(98.0)


def test_select_occurrence_rejects_empty_table() -> None:
    with pytest.raises(ValidationError, match="empty"):
        build_inspection_selection(
            pl.DataFrame(),
            pl.DataFrame(),
            occurrence_index=0,
            horizon_bars=5,
        )
