"""Unit tests for gated strategy entry signal construction."""

from __future__ import annotations

from datetime import UTC, datetime

import polars as pl

from trading_framework.application.strategy_research.entry_signals import build_gated_entry_signals


def test_build_gated_entry_signals_filters_by_market_state() -> None:
    available_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    later_at = datetime(2024, 1, 1, 12, 1, tzinfo=UTC)
    signal_emissions = pl.DataFrame(
        {
            "available_at": [available_at, later_at],
            "direction": ["long", "long"],
        }
    )
    market_state = pl.DataFrame(
        {
            "available_at": [available_at, later_at],
            "model_result": [True, False],
        }
    )

    gated = build_gated_entry_signals(
        signal_emissions=signal_emissions,
        market_state=market_state,
    )

    assert len(gated) == 1
    assert gated.row(0, named=True)["available_at"] == available_at
