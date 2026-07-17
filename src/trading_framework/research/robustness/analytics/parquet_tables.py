"""Build Robustness analytics Parquet tables for dashboard dual-write."""

from __future__ import annotations

import json
from typing import Any

import polars as pl

from trading_framework.research.robustness.analytics.monte_carlo import MonteCarloAnalytics
from trading_framework.research.robustness.analytics.parameter_sweep import ParameterSweepAnalytics
from trading_framework.research.robustness.analytics.stress import StressTestAnalytics
from trading_framework.research.robustness.analytics.walk_forward import WalkForwardAnalytics


def parameter_sweep_parquet_tables(analytics: ParameterSweepAnalytics) -> dict[str, pl.DataFrame]:
    """Flatten parameter-sweep analytics into dashboard Parquet tables."""
    payload = analytics.to_dict()
    experiment_id = str(payload["experiment_id"])
    rankings = [
        {
            "experiment_id": experiment_id,
            "ranking_metric": payload["ranking_metric"],
            "rank": int(row["rank"]),
            "config_id": str(row["config_id"]),
            "parameter_overrides": json.dumps(row["parameter_overrides"], sort_keys=True),
            "strategy_run_id": str(row["strategy_run_id"]),
            "metric": str(row["metric"]),
            "metric_value": _optional_float(row.get("metric_value")),
            "net_pnl": str(row["net_pnl"]),
            "max_drawdown": str(row["max_drawdown"]),
            "win_rate": _optional_float(row.get("win_rate")),
            "trade_count": int(row["trade_count"]),
        }
        for row in payload["rankings"]
    ]
    heatmap_rows: list[dict[str, Any]] = []
    for heatmap in payload["heatmaps"]:
        y_values = heatmap.get("y_values") or [""]
        for y_index, y_value in enumerate(y_values):
            row_values = heatmap["values"][y_index]
            for x_index, x_value in enumerate(heatmap["x_values"]):
                heatmap_rows.append(
                    {
                        "experiment_id": experiment_id,
                        "metric": str(heatmap["metric"]),
                        "x_axis": str(heatmap["x_axis"]),
                        "y_axis": heatmap.get("y_axis"),
                        "x_value": str(x_value),
                        "y_value": str(y_value) if y_value != "" else None,
                        "value": _optional_float(row_values[x_index]),
                    }
                )
    tables = {
        "parameter_sweep_rankings": _frame_or_empty(
            rankings,
            schema={
                "experiment_id": pl.Utf8,
                "ranking_metric": pl.Utf8,
                "rank": pl.Int64,
                "config_id": pl.Utf8,
                "parameter_overrides": pl.Utf8,
                "strategy_run_id": pl.Utf8,
                "metric": pl.Utf8,
                "metric_value": pl.Float64,
                "net_pnl": pl.Utf8,
                "max_drawdown": pl.Utf8,
                "win_rate": pl.Float64,
                "trade_count": pl.Int64,
            },
        ),
        "parameter_sweep_heatmap": _frame_or_empty(
            heatmap_rows,
            schema={
                "experiment_id": pl.Utf8,
                "metric": pl.Utf8,
                "x_axis": pl.Utf8,
                "y_axis": pl.Utf8,
                "x_value": pl.Utf8,
                "y_value": pl.Utf8,
                "value": pl.Float64,
            },
        ),
    }
    return tables


def walk_forward_parquet_tables(analytics: WalkForwardAnalytics) -> dict[str, pl.DataFrame]:
    """Flatten walk-forward analytics into dashboard Parquet tables."""
    payload = analytics.to_dict()
    experiment_id = str(payload["experiment_id"])
    fold_rows = []
    for item in payload["fold_evaluations"]:
        selection = item["selection"]
        oos = item["oos_summary"]
        fold_rows.append(
            {
                "experiment_id": experiment_id,
                "fold_id": str(selection["fold_id"]),
                "fold_index": int(selection["fold_index"]),
                "config_id": str(selection["config_id"]),
                "train_net_pnl": str(selection["train_net_pnl"]),
                "oos_strategy_run_id": str(item["oos_strategy_run_id"]),
                "oos_trade_count": int(oos["trade_count"]),
                "oos_net_pnl": str(oos["net_pnl"]),
                "oos_max_drawdown": str(oos["max_drawdown"]),
                "oos_final_equity": str(oos["final_equity"]),
            }
        )
    equity = analytics.stitched_oos_equity.equity
    if equity.height == 0:
        equity_frame = pl.DataFrame(
            schema={
                "experiment_id": pl.Utf8,
                "observed_at": pl.Datetime(time_unit="us", time_zone="UTC"),
                "equity": pl.Float64,
                "drawdown": pl.Float64,
            }
        )
    else:
        equity_frame = equity.select(
            pl.lit(experiment_id).alias("experiment_id"),
            "observed_at",
            "equity",
            "drawdown",
        )
    return {
        "walk_forward_folds": _frame_or_empty(
            fold_rows,
            schema={
                "experiment_id": pl.Utf8,
                "fold_id": pl.Utf8,
                "fold_index": pl.Int64,
                "config_id": pl.Utf8,
                "train_net_pnl": pl.Utf8,
                "oos_strategy_run_id": pl.Utf8,
                "oos_trade_count": pl.Int64,
                "oos_net_pnl": pl.Utf8,
                "oos_max_drawdown": pl.Utf8,
                "oos_final_equity": pl.Utf8,
            },
        ),
        "walk_forward_equity": equity_frame,
    }


def stress_parquet_tables(analytics: StressTestAnalytics) -> dict[str, pl.DataFrame]:
    """Flatten stress analytics into one comparison table."""
    payload = analytics.to_dict()
    experiment_id = str(payload["experiment_id"])
    rows = [
        {
            "experiment_id": experiment_id,
            "baseline_strategy_run_id": payload["baseline_strategy_run_id"],
            "baseline_net_pnl": str(payload["baseline_net_pnl"]),
            "baseline_trade_count": int(payload["baseline_trade_count"]),
            "scenario_id": str(row["scenario_id"]),
            "mode": str(row["mode"]),
            "status": str(row["status"]),
            "net_pnl": None if row.get("net_pnl") is None else str(row["net_pnl"]),
            "trade_count": row.get("trade_count"),
            "delta_net_pnl": (
                None if row.get("delta_net_pnl") is None else str(row["delta_net_pnl"])
            ),
            "strategy_run_id": row.get("strategy_run_id"),
        }
        for row in payload["rows"]
    ]
    return {
        "stress_comparison": _frame_or_empty(
            rows,
            schema={
                "experiment_id": pl.Utf8,
                "baseline_strategy_run_id": pl.Utf8,
                "baseline_net_pnl": pl.Utf8,
                "baseline_trade_count": pl.Int64,
                "scenario_id": pl.Utf8,
                "mode": pl.Utf8,
                "status": pl.Utf8,
                "net_pnl": pl.Utf8,
                "trade_count": pl.Int64,
                "delta_net_pnl": pl.Utf8,
                "strategy_run_id": pl.Utf8,
            },
        )
    }


def monte_carlo_parquet_tables(analytics: MonteCarloAnalytics) -> dict[str, pl.DataFrame]:
    """Flatten Monte Carlo distribution/tail summaries for the dashboard."""
    payload = analytics.to_dict()
    experiment_id = str(payload["experiment_id"])
    distributions = [
        {
            "experiment_id": experiment_id,
            **{key: row.get(key) for key in row},
        }
        for row in payload.get("distribution_summaries", [])
    ]
    # Normalize common fields to strings/floats where present.
    normalized = []
    for row in distributions:
        normalized.append(
            {
                "experiment_id": experiment_id,
                "method": str(row.get("method", "")),
                "path_count": int(row["path_count"]) if row.get("path_count") is not None else None,
                "mean_terminal_equity": _optional_float(row.get("mean_terminal_equity")),
                "p5_terminal_equity": _optional_float(row.get("p5_terminal_equity")),
                "p50_terminal_equity": _optional_float(row.get("p50_terminal_equity")),
                "p95_terminal_equity": _optional_float(row.get("p95_terminal_equity")),
            }
        )
    tails = []
    for row in payload.get("tail_probabilities", []):
        tails.append(
            {
                "experiment_id": experiment_id,
                "method": str(row.get("method", "")),
                "probability_terminal_pnl_negative": _optional_float(
                    row.get("probability_terminal_pnl_negative")
                ),
                "probability_max_drawdown_exceeds_threshold": _optional_float(
                    row.get("probability_max_drawdown_exceeds_threshold")
                ),
            }
        )
    return {
        "monte_carlo_distributions": _frame_or_empty(
            normalized,
            schema={
                "experiment_id": pl.Utf8,
                "method": pl.Utf8,
                "path_count": pl.Int64,
                "mean_terminal_equity": pl.Float64,
                "p5_terminal_equity": pl.Float64,
                "p50_terminal_equity": pl.Float64,
                "p95_terminal_equity": pl.Float64,
            },
        ),
        "monte_carlo_tails": _frame_or_empty(
            tails,
            schema={
                "experiment_id": pl.Utf8,
                "method": pl.Utf8,
                "probability_terminal_pnl_negative": pl.Float64,
                "probability_max_drawdown_exceeds_threshold": pl.Float64,
            },
        ),
    }


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _frame_or_empty(rows: list[dict[str, Any]], *, schema: dict[str, Any]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame(schema=schema)
    return pl.DataFrame(rows).select(list(schema))
