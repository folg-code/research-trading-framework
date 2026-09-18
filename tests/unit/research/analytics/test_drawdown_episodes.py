"""Tests for drawdown-episode extraction (Phase 18 18A Milestone 1a / Sprint 068)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl

from trading_framework.research.analytics.drawdown_episodes import (
    DRAWDOWN_EPISODES_SCHEMA_VERSION,
    compute_drawdown_episodes,
    empty_drawdown_episodes_dataframe,
)
from trading_framework.research.simulation.facts import empty_equity_points_dataframe


def _equity_frame(values: list[float]) -> pl.DataFrame:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    return pl.DataFrame(
        {
            "observed_at": [start + timedelta(minutes=i) for i in range(len(values))],
            "equity": values,
            "drawdown": [0.0] * len(values),
            "open_position_count": [0] * len(values),
        }
    ).select(empty_equity_points_dataframe().columns)


def test_compute_drawdown_episodes_empty_equity_returns_empty_frame() -> None:
    result = compute_drawdown_episodes(run_id="r1", equity=empty_equity_points_dataframe())
    assert result.height == 0
    assert result.columns == empty_drawdown_episodes_dataframe().columns


def test_compute_drawdown_episodes_monotonic_equity_has_no_episodes() -> None:
    equity = _equity_frame([100.0, 110.0, 120.0, 130.0])
    result = compute_drawdown_episodes(run_id="r1", equity=equity)
    assert result.height == 0


def test_compute_drawdown_episodes_one_recovered_episode() -> None:
    # peak 100 -> trough 80 -> recovers to 100 at index 3
    equity = _equity_frame([100.0, 90.0, 80.0, 100.0, 105.0])
    result = compute_drawdown_episodes(run_id="r1", equity=equity)
    assert result.height == 1
    row = result.to_dicts()[0]
    assert row["schema_version"] == DRAWDOWN_EPISODES_SCHEMA_VERSION
    assert row["run_id"] == "r1"
    assert row["episode_id"] == 0
    assert row["peak_equity"] == 100.0
    assert row["trough_equity"] == 80.0
    assert row["depth_pct"] == 80.0 / 100.0 - 1.0
    assert row["duration_bars"] == 2  # index 0 -> index 2
    assert row["recovery_bars"] == 1  # index 2 -> index 3


def test_compute_drawdown_episodes_unresolved_episode_has_null_recovery() -> None:
    equity = _equity_frame([100.0, 90.0, 80.0, 85.0])
    result = compute_drawdown_episodes(run_id="r1", equity=equity)
    assert result.height == 1
    row = result.to_dicts()[0]
    assert row["recovery_bars"] is None
    assert row["trough_equity"] == 80.0


def test_compute_drawdown_episodes_two_sequential_episodes() -> None:
    equity = _equity_frame([100.0, 80.0, 100.0, 50.0, 100.0])
    result = compute_drawdown_episodes(run_id="r1", equity=equity)
    assert result.height == 2
    first, second = result.to_dicts()
    assert first["episode_id"] == 0
    assert first["trough_equity"] == 80.0
    assert first["recovery_bars"] == 1
    assert second["episode_id"] == 1
    assert second["trough_equity"] == 50.0
    assert second["recovery_bars"] == 1


def test_compute_drawdown_episodes_no_minimum_depth_threshold() -> None:
    equity = _equity_frame([100.0, 99.99, 100.0])
    result = compute_drawdown_episodes(run_id="r1", equity=equity)
    assert result.height == 1
    assert result.to_dicts()[0]["depth_pct"] < 0.0
