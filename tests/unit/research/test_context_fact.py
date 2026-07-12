"""Unit tests for ContextFact alignment at signal available_at."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl

from trading_framework.research import align_context_facts_at_available_at


def _occurrences(*, available_at: datetime) -> pl.DataFrame:
    detected_at = datetime(2024, 1, 1, tzinfo=UTC)
    return pl.DataFrame(
        {
            "occurrence_id": ["occ-1"],
            "signal_model_id": ["controlled_signal"],
            "detected_at": [detected_at],
            "available_at": [available_at],
            "direction": ["long"],
            "reference_price": [100.0],
            "instrument": ["TEST"],
            "evaluation_timeframe": ["1m"],
            "source_dataset_ref": ["test"],
        }
    )


def test_context_evaluated_at_signal_available_at_when_state_is_true() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=index) for index in range(4))
    market_state = pl.DataFrame(
        {
            "timestamp": list(timestamps),
            "available_at": list(timestamps),
            "model_result": [False, False, True, True],
            "market_model_id": ["high_volatility"] * 4,
        }
    )
    context = align_context_facts_at_available_at(
        _occurrences(available_at=timestamps[2]),
        market_state,
        market_model_id="high_volatility",
    )
    row = context.row(0, named=True)
    assert row["context_met_at_available_at"] is True
    assert row["context_evaluated_at"] == timestamps[2]


def test_context_false_before_market_state_turns_true() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=index) for index in range(4))
    market_state = pl.DataFrame(
        {
            "timestamp": list(timestamps),
            "available_at": list(timestamps),
            "model_result": [False, False, True, True],
            "market_model_id": ["high_volatility"] * 4,
        }
    )
    context = align_context_facts_at_available_at(
        _occurrences(available_at=timestamps[1]),
        market_state,
        market_model_id="high_volatility",
    )
    row = context.row(0, named=True)
    assert row["context_met_at_available_at"] is False


def test_context_uses_available_at_not_future_state() -> None:
    start = datetime(2024, 1, 2, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=index) for index in range(4))
    market_state = pl.DataFrame(
        {
            "timestamp": list(timestamps),
            "available_at": list(timestamps),
            "model_result": [False, False, False, True],
            "market_model_id": ["high_volatility"] * 4,
        }
    )
    context = align_context_facts_at_available_at(
        _occurrences(available_at=timestamps[2]),
        market_state,
        market_model_id="high_volatility",
    )
    row = context.row(0, named=True)
    assert row["context_met_at_available_at"] is False
