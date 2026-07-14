"""Unit tests for simulation compile layer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import numpy as np
import polars as pl
import pytest

from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketBar
from trading_framework.research.simulation.compile import (
    CompileSimulationInputError,
    compile_simulation_input,
    datetime_to_epoch_ns,
    resolve_signal_bar_index,
)
from trading_framework.research.simulation.input import (
    SIGNAL_DIRECTION_LONG,
    SIGNAL_DIRECTION_SHORT,
    UNRESOLVED_BAR_INDEX,
)


def _bar(minute: int) -> MarketBar:
    observed_at = datetime(2024, 1, 1, 12, minute, tzinfo=UTC)
    return MarketBar(
        open=Price(Decimal("100")),
        high=Price(Decimal("105")),
        low=Price(Decimal("99")),
        close=Price(Decimal("103")),
        volume=Volume(1000),
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
    )


def test_compile_simulation_input_materializes_bar_arrays() -> None:
    bars = [_bar(0), _bar(1), _bar(2)]
    compiled = compile_simulation_input(
        bars=bars,
        entry_signals=pl.DataFrame(
            schema={
                "available_at": pl.Datetime(time_unit="us", time_zone="UTC"),
                "direction": pl.String,
            }
        ),
    )

    assert compiled.bars.bar_count == 3
    assert compiled.bars.observed_at_ns.dtype == np.int64
    assert compiled.bars.open_prices.tolist() == [100.0, 100.0, 100.0]
    assert compiled.bars.close_prices.tolist() == [103.0, 103.0, 103.0]
    assert compiled.entry_signals.available_at_ns.shape == (0,)


def test_compile_entry_signals_resolves_observed_and_available_at() -> None:
    bars = [_bar(0), _bar(1)]
    entry_signals = pl.DataFrame(
        {
            "available_at": [bars[0].observed_at, bars[1].available_at],
            "direction": ["long", "short"],
        }
    )

    compiled = compile_simulation_input(bars=bars, entry_signals=entry_signals)

    assert compiled.entry_signals.signal_bar_index.tolist() == [0, 1]
    assert compiled.entry_signals.direction.tolist() == [
        SIGNAL_DIRECTION_LONG,
        SIGNAL_DIRECTION_SHORT,
    ]
    assert compiled.entry_signals.available_at_ns.tolist() == [
        datetime_to_epoch_ns(bars[0].observed_at),
        datetime_to_epoch_ns(bars[1].available_at),
    ]


def test_compile_entry_signals_marks_unknown_timestamp_as_unresolved() -> None:
    bars = [_bar(0)]
    unknown_at = datetime(2024, 1, 1, 13, 0, tzinfo=UTC)
    entry_signals = pl.DataFrame(
        {
            "available_at": [unknown_at],
            "direction": ["long"],
        }
    )

    compiled = compile_simulation_input(bars=bars, entry_signals=entry_signals)

    assert compiled.entry_signals.signal_bar_index.tolist() == [UNRESOLVED_BAR_INDEX]


def test_compile_entry_signals_keeps_first_bar_on_duplicate_observed_at() -> None:
    shared_observed_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    bars = [
        MarketBar(
            open=Price(Decimal("100")),
            high=Price(Decimal("101")),
            low=Price(Decimal("99")),
            close=Price(Decimal("100")),
            volume=Volume(1),
            observed_at=shared_observed_at,
            available_at=shared_observed_at + timedelta(minutes=1),
        ),
        MarketBar(
            open=Price(Decimal("101")),
            high=Price(Decimal("102")),
            low=Price(Decimal("100")),
            close=Price(Decimal("101")),
            volume=Volume(1),
            observed_at=shared_observed_at,
            available_at=shared_observed_at + timedelta(minutes=2),
        ),
    ]
    entry_signals = pl.DataFrame(
        {
            "available_at": [shared_observed_at],
            "direction": ["long"],
        }
    )

    compiled = compile_simulation_input(bars=bars, entry_signals=entry_signals)

    assert compiled.entry_signals.signal_bar_index.tolist() == [0]


def test_resolve_signal_bar_index_prefers_observed_at_match() -> None:
    observed_at_to_index = {100: 0}
    available_at_to_index = {200: 1}

    assert (
        resolve_signal_bar_index(
            observed_at_to_index=observed_at_to_index,
            available_at_to_index=available_at_to_index,
            available_at_ns=100,
        )
        == 0
    )
    assert (
        resolve_signal_bar_index(
            observed_at_to_index=observed_at_to_index,
            available_at_to_index=available_at_to_index,
            available_at_ns=200,
        )
        == 1
    )


def test_compile_entry_signals_rejects_unsupported_direction() -> None:
    bars = [_bar(0)]
    entry_signals = pl.DataFrame(
        {
            "available_at": [bars[0].observed_at],
            "direction": ["neutral"],
        }
    )

    with pytest.raises(CompileSimulationInputError, match="unsupported entry signal direction"):
        compile_simulation_input(bars=bars, entry_signals=entry_signals)
