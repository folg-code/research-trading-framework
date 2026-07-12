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
