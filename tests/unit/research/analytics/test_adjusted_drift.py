"""Tests for adjusted forward drift (Phase 18 18B Milestone 1 / Sprint 073)."""

from __future__ import annotations

import polars as pl
import pytest

from trading_framework.research.analytics.adjusted_drift import (
    ADJUSTED_FORWARD_DRIFT_SCHEMA_VERSION,
    compute_adjusted_forward_drift,
    empty_adjusted_forward_drift_dataframe,
)


def _grouped_summaries(rows: list[dict[str, object]]) -> pl.DataFrame:
    return pl.DataFrame(rows)


def _summary_metrics(rows: list[dict[str, object]]) -> pl.DataFrame:
    return pl.DataFrame(rows)


def test_compute_adjusted_forward_drift_empty_when_no_grouped_summaries() -> None:
    result = compute_adjusted_forward_drift(
        run_id="r1",
        grouped_summaries=pl.DataFrame(schema={"horizon_bars": pl.Int64()}),
        summary_metrics=_summary_metrics([{"horizon_bars": 5, "forward_return_mean": 0.001}]),
    )
    assert result.height == 0
    assert result.columns == empty_adjusted_forward_drift_dataframe().columns


def test_compute_adjusted_forward_drift_empty_when_no_summary_metrics() -> None:
    result = compute_adjusted_forward_drift(
        run_id="r1",
        grouped_summaries=_grouped_summaries(
            [
                {
                    "horizon_bars": 5,
                    "group_dimension": "calendar_month",
                    "group_value": "2025-01",
                    "sample_size_complete": 100,
                    "forward_return_mean": 0.002,
                }
            ]
        ),
        summary_metrics=pl.DataFrame(schema={"horizon_bars": pl.Int64()}),
    )
    assert result.height == 0


def test_compute_adjusted_forward_drift_large_sample_stays_close_to_raw_mean() -> None:
    result = compute_adjusted_forward_drift(
        run_id="r1",
        grouped_summaries=_grouped_summaries(
            [
                {
                    "horizon_bars": 5,
                    "group_dimension": "calendar_month",
                    "group_value": "2025-01",
                    "sample_size_complete": 10_000,
                    "forward_return_mean": 0.01,
                }
            ]
        ),
        summary_metrics=_summary_metrics([{"horizon_bars": 5, "forward_return_mean": 0.0}]),
        prior_strength=100,
    )
    assert result.height == 1
    row = result.to_dicts()[0]
    assert row["schema_version"] == ADJUSTED_FORWARD_DRIFT_SCHEMA_VERSION
    assert row["shrinkage_weight"] == pytest.approx(10_000 / 10_100, abs=1e-4)
    assert row["adjusted_forward_return_mean"] == pytest.approx(0.01, abs=1e-3)


def test_compute_adjusted_forward_drift_small_sample_shrinks_toward_global_mean() -> None:
    result = compute_adjusted_forward_drift(
        run_id="r1",
        grouped_summaries=_grouped_summaries(
            [
                {
                    "horizon_bars": 5,
                    "group_dimension": "calendar_month",
                    "group_value": "2025-01",
                    "sample_size_complete": 1,
                    "forward_return_mean": 0.5,
                }
            ]
        ),
        summary_metrics=_summary_metrics([{"horizon_bars": 5, "forward_return_mean": 0.0}]),
        prior_strength=100,
    )
    row = result.to_dicts()[0]
    assert row["shrinkage_weight"] == pytest.approx(1 / 101, abs=1e-4)
    assert row["adjusted_forward_return_mean"] == pytest.approx(0.5 / 101, abs=1e-3)


def test_compute_adjusted_forward_drift_joins_on_horizon() -> None:
    result = compute_adjusted_forward_drift(
        run_id="r1",
        grouped_summaries=_grouped_summaries(
            [
                {
                    "horizon_bars": 5,
                    "group_dimension": "d",
                    "group_value": "a",
                    "sample_size_complete": 10,
                    "forward_return_mean": 0.1,
                },
                {
                    "horizon_bars": 15,
                    "group_dimension": "d",
                    "group_value": "a",
                    "sample_size_complete": 10,
                    "forward_return_mean": 0.2,
                },
            ]
        ),
        summary_metrics=_summary_metrics(
            [
                {"horizon_bars": 5, "forward_return_mean": 0.0},
                {"horizon_bars": 15, "forward_return_mean": 1.0},
            ]
        ),
    )
    by_horizon = {row["horizon_bars"]: row for row in result.to_dicts()}
    assert by_horizon[5]["global_forward_return_mean"] == 0.0
    assert by_horizon[15]["global_forward_return_mean"] == 1.0
