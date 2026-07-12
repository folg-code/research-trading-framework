"""Shared metric helpers for Signal Research analytics aggregates."""

from __future__ import annotations

import polars as pl


def aggregate_complete_metrics(complete: pl.DataFrame) -> dict[str, float | None]:
    """Compute aggregate metrics over filter-eligible complete rows."""
    if len(complete) == 0:
        return {
            "forward_return_mean": None,
            "forward_return_median": None,
            "hit_rate": None,
            "mfe_mean": None,
            "mfe_median": None,
            "mae_mean": None,
            "mae_median": None,
        }
    returns = complete["forward_return"]
    hits = complete.filter(pl.col("forward_return") > 0).height
    return {
        "forward_return_mean": float(returns.mean()),  # type: ignore[arg-type]
        "forward_return_median": float(returns.median()),  # type: ignore[arg-type]
        "hit_rate": hits / len(complete),
        "mfe_mean": float(complete["mfe"].mean()),  # type: ignore[arg-type]
        "mfe_median": float(complete["mfe"].median()),  # type: ignore[arg-type]
        "mae_mean": float(complete["mae"].mean()),  # type: ignore[arg-type]
        "mae_median": float(complete["mae"].median()),  # type: ignore[arg-type]
    }


def aggregate_distribution_metrics(complete: pl.DataFrame) -> dict[str, float | None]:
    """Compute distribution diagnostics over filter-eligible complete rows."""
    if len(complete) == 0:
        return {
            "forward_return_p10": None,
            "forward_return_p25": None,
            "forward_return_p75": None,
            "forward_return_p90": None,
            "forward_return_std": None,
            "forward_return_min": None,
            "forward_return_max": None,
        }
    returns = complete["forward_return"]
    quantiles = returns.quantile([0.1, 0.25, 0.75, 0.9], interpolation="linear")
    return {
        "forward_return_p10": float(quantiles[0]),  # type: ignore[arg-type]
        "forward_return_p25": float(quantiles[1]),  # type: ignore[arg-type]
        "forward_return_p75": float(quantiles[2]),  # type: ignore[arg-type]
        "forward_return_p90": float(quantiles[3]),  # type: ignore[arg-type]
        "forward_return_std": float(returns.std(ddof=0)),  # type: ignore[arg-type]
        "forward_return_min": float(returns.min()),  # type: ignore[arg-type]
        "forward_return_max": float(returns.max()),  # type: ignore[arg-type]
    }
