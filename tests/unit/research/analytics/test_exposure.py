"""Tests for notional exposure / equity ratio (Phase 18 18A Milestone 1a / Sprint 068)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl

from trading_framework.research.analytics.exposure import (
    EXPOSURE_SCHEMA_VERSION,
    compute_exposure,
    empty_exposure_dataframe,
)
from trading_framework.research.simulation.facts import (
    empty_equity_points_dataframe,
    empty_simulated_trades_dataframe,
)

_START = datetime(2024, 1, 1, tzinfo=UTC)


def _equity_frame(values: list[float]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "observed_at": [_START + timedelta(minutes=i) for i in range(len(values))],
            "equity": values,
            "drawdown": [0.0] * len(values),
            "open_position_count": [0] * len(values),
        }
    ).select(empty_equity_points_dataframe().columns)


def _trade_row(
    *, entry_offset: int, exit_offset: int, quantity: float, entry_price: float
) -> dict[str, object]:
    return {
        "trade_id": f"t-{entry_offset}-{exit_offset}",
        "strategy_model_id": "s",
        "instrument": "BTCUSDT.P",
        "direction": "long",
        "entry_signal_at": _START + timedelta(minutes=entry_offset),
        "entry_fill_at": _START + timedelta(minutes=entry_offset),
        "entry_fill_price": entry_price,
        "exit_signal_at": _START + timedelta(minutes=exit_offset),
        "exit_fill_at": _START + timedelta(minutes=exit_offset),
        "exit_fill_price": entry_price,
        "quantity": quantity,
        "gross_pnl": 0.0,
        "commission_paid": 0.0,
        "net_pnl": 0.0,
        "bars_held": exit_offset - entry_offset,
        "exit_reason": "test",
        "source_dataset_ref": "dataset@1",
    }


def _trades_frame(rows: list[dict[str, object]]) -> pl.DataFrame:
    if not rows:
        return empty_simulated_trades_dataframe()
    return pl.DataFrame(rows).select(empty_simulated_trades_dataframe().columns)


def test_compute_exposure_empty_equity_returns_empty_frame() -> None:
    result = compute_exposure(
        run_id="r1",
        trades=empty_simulated_trades_dataframe(),
        equity=empty_equity_points_dataframe(),
    )
    assert result.height == 0
    assert result.columns == empty_exposure_dataframe().columns


def test_compute_exposure_no_trades_is_all_zero_notional() -> None:
    equity = _equity_frame([100.0, 100.0, 100.0])
    result = compute_exposure(run_id="r1", trades=empty_simulated_trades_dataframe(), equity=equity)
    assert result.height == 3
    assert result["notional_exposure"].to_list() == [0.0, 0.0, 0.0]
    assert result["exposure_ratio"].to_list() == [0.0, 0.0, 0.0]


def test_compute_exposure_one_open_trade() -> None:
    # trade open from minute 1 (inclusive) to minute 3 (exclusive)
    equity = _equity_frame([100.0, 100.0, 100.0, 100.0])
    trades = _trades_frame(
        [_trade_row(entry_offset=1, exit_offset=3, quantity=2.0, entry_price=50.0)]
    )
    result = compute_exposure(run_id="r1", trades=trades, equity=equity)
    assert result.height == 4
    rows = result.to_dicts()
    assert rows[0]["schema_version"] == EXPOSURE_SCHEMA_VERSION
    assert rows[0]["run_id"] == "r1"
    assert [r["notional_exposure"] for r in rows] == [0.0, 100.0, 100.0, 0.0]
    assert [r["exposure_ratio"] for r in rows] == [0.0, 1.0, 1.0, 0.0]


def test_compute_exposure_ratio_is_null_for_non_positive_equity() -> None:
    equity = _equity_frame([100.0, -50.0, 0.0])
    trades = _trades_frame(
        [_trade_row(entry_offset=0, exit_offset=3, quantity=1.0, entry_price=10.0)]
    )
    result = compute_exposure(run_id="r1", trades=trades, equity=equity)
    ratios = result["exposure_ratio"].to_list()
    assert ratios[0] == 10.0 / 100.0
    assert ratios[1] is None
    assert ratios[2] is None


def test_compute_exposure_sums_overlapping_trades() -> None:
    equity = _equity_frame([100.0, 100.0])
    trades = _trades_frame(
        [
            _trade_row(entry_offset=0, exit_offset=2, quantity=1.0, entry_price=10.0),
            _trade_row(entry_offset=0, exit_offset=2, quantity=2.0, entry_price=5.0),
        ]
    )
    result = compute_exposure(run_id="r1", trades=trades, equity=equity)
    assert result["notional_exposure"].to_list() == [20.0, 20.0]
