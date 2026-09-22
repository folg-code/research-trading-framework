"""Post-hoc walk-forward fold geometry and stability summary.

Phase 18, 18D Milestone 1 (Sprint 075) / D-P18D-01/02. Both artifacts are
computed once, post-hoc, from data a walk-forward experiment already
persists -- the fold date ranges in ``folds/plan.json`` (read via
``WalkForwardFoldPlan``, never re-planned here) and the per-fold PnL
already written to ``analytics/walk_forward_folds.parquet``. Neither
function reruns the backtester or the fold planner.
"""

from __future__ import annotations

from datetime import datetime

import polars as pl

from trading_framework.research.robustness.walk_forward import WalkForwardFoldPlan

FOLD_GEOMETRY_SCHEMA_VERSION = "robustness_walk_forward_fold_geometry.v1"
STABILITY_SCHEMA_VERSION = "robustness_walk_forward_stability.v1"

#: Metrics summarized by compute_walk_forward_stability, and whether each
#: gets a pct_profitable_folds figure (D-P18D-01: OOS profitability is
#: decision-relevant; train-window profitability is not).
_STABILITY_METRICS: tuple[tuple[str, bool], ...] = (
    ("oos_net_pnl", True),
    ("train_net_pnl", False),
)


def walk_forward_fold_geometry_schema() -> dict[str, pl.DataType]:
    return {
        "schema_version": pl.String(),
        "experiment_id": pl.String(),
        "fold_id": pl.String(),
        "fold_index": pl.Int64(),
        "train_range_start": pl.Datetime(time_unit="us", time_zone="UTC"),
        "train_range_end": pl.Datetime(time_unit="us", time_zone="UTC"),
        "oos_range_start": pl.Datetime(time_unit="us", time_zone="UTC"),
        "oos_range_end": pl.Datetime(time_unit="us", time_zone="UTC"),
        "train_overlap_seconds_with_previous_fold": pl.Int64(),
    }


def walk_forward_stability_schema() -> dict[str, pl.DataType]:
    return {
        "schema_version": pl.String(),
        "experiment_id": pl.String(),
        "metric": pl.String(),
        "fold_count": pl.Int64(),
        "mean": pl.Float64(),
        "std": pl.Float64(),
        "min": pl.Float64(),
        "max": pl.Float64(),
        "pct_profitable_folds": pl.Float64(),
    }


def empty_walk_forward_fold_geometry_dataframe() -> pl.DataFrame:
    return pl.DataFrame(schema=walk_forward_fold_geometry_schema())


def empty_walk_forward_stability_dataframe() -> pl.DataFrame:
    return pl.DataFrame(schema=walk_forward_stability_schema())


def compute_walk_forward_fold_geometry(
    *, experiment_id: str, plan: WalkForwardFoldPlan
) -> pl.DataFrame:
    """Per-fold date ranges plus overlap with the previous fold's train window.

    ``train_overlap_seconds_with_previous_fold`` is a proper interval
    intersection (D-P18D-02) -- correct for both ``ROLLING`` (partial
    overlap or none) and ``EXPANDING`` (full containment of every prior
    fold's train window) -- not the narrower "previous end minus this
    start" formula that only holds for ``ROLLING``. ``0`` for the first
    fold, which has no previous fold to overlap.
    """
    if not plan.folds:
        return empty_walk_forward_fold_geometry_dataframe()

    folds_sorted = sorted(plan.folds, key=lambda fold: fold.fold_index)
    rows: list[dict[str, object]] = []
    previous_train_start: datetime | None = None
    previous_train_end: datetime | None = None
    for fold in folds_sorted:
        if previous_train_end is None or previous_train_start is None:
            overlap_seconds = 0
        else:
            overlap_start = max(previous_train_start, fold.train_range.start)
            overlap_end = min(previous_train_end, fold.train_range.end)
            overlap_seconds = max(0, int((overlap_end - overlap_start).total_seconds()))
        rows.append(
            {
                "schema_version": FOLD_GEOMETRY_SCHEMA_VERSION,
                "experiment_id": experiment_id,
                "fold_id": fold.fold_id,
                "fold_index": fold.fold_index,
                "train_range_start": fold.train_range.start,
                "train_range_end": fold.train_range.end,
                "oos_range_start": fold.oos_range.start,
                "oos_range_end": fold.oos_range.end,
                "train_overlap_seconds_with_previous_fold": overlap_seconds,
            }
        )
        previous_train_start = fold.train_range.start
        previous_train_end = fold.train_range.end
    return pl.DataFrame(rows, schema=walk_forward_fold_geometry_schema())


def compute_walk_forward_stability(*, experiment_id: str, folds: pl.DataFrame) -> pl.DataFrame:
    """Mean/std/min/max (+ pct-profitable for OOS) over already-persisted fold PnL.

    Coefficient of variation is deliberately not computed (D-P18D-01):
    checked against the real 14-fold distribution, it produced a
    meaningless, sign-flipping ratio when the mean straddles zero.
    """
    if folds.height == 0:
        return empty_walk_forward_stability_dataframe()

    rows: list[dict[str, object]] = []
    for metric_name, include_pct_profitable in _STABILITY_METRICS:
        if metric_name not in folds.columns:
            continue
        series = folds[metric_name].cast(pl.Float64)
        profitable_fraction = (series > 0).cast(pl.Float64).mean()
        rows.append(
            {
                "schema_version": STABILITY_SCHEMA_VERSION,
                "experiment_id": experiment_id,
                "metric": metric_name,
                "fold_count": series.len(),
                "mean": series.mean(),
                "std": series.std(),
                "min": series.min(),
                "max": series.max(),
                "pct_profitable_folds": (profitable_fraction if include_pct_profitable else None),
            }
        )
    if not rows:
        return empty_walk_forward_stability_dataframe()
    return pl.DataFrame(rows, schema=walk_forward_stability_schema())
