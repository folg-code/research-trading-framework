"""Spike-only Signal Research analytics helpers (S010 Wave 0+).

Grouping and conditional helpers remain spike-only until Wave 3 promotion.
Production frame builder, filters, schemas and RunSummary live in ``research/analytics/``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.analytics.aggregates import (
    aggregate_complete_metrics,
    compute_run_summary,
)
from trading_framework.research.analytics.dimensions import (
    AnalyticsTimestampBasis,
    GroupDimension,
)
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.frame_builder import build_analysis_frame
from trading_framework.time.sessions import CmeEsRthSessionResolver
from trading_framework.time.sessions.constants import ES_RTH_SESSION_ID

FORBIDDEN_ANALYTICS_IMPORTS = frozenset(
    {
        "evaluate_models",
        "compute_forward_outcomes",
        "compute_forward_outcomes_for_horizons",
        "materialize_signal_occurrences",
        "materialize_market_model_observations",
        "align_context_facts_at_available_at",
    }
)

_ANALYTICS_MODULE_DIR = (
    Path(__file__).resolve().parents[2] / "src" / "trading_framework" / "research" / "analytics"
)


@dataclass(frozen=True, slots=True)
class ConditionalComparisonRow:
    run_id: str
    horizon_bars: int
    context_true_sample_size: int
    context_false_sample_size: int
    forward_return_mean_true: float | None
    forward_return_mean_false: float | None
    forward_return_mean_delta: float | None
    hit_rate_true: float | None
    hit_rate_false: float | None
    hit_rate_delta: float | None


def assert_read_only_analytics_package() -> None:
    """Fail if production analytics modules import forbidden compute paths."""
    for path in sorted(_ANALYTICS_MODULE_DIR.glob("*.py")):
        assert_read_only_module(path.read_text(encoding="utf-8"), source=str(path.name))


def assert_read_only_module(source_text: str, *, source: str = "module") -> None:
    """Fail if analytics module imports forbidden compute paths."""
    for line in source_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(("import ", "from ")):
            continue
        for forbidden in FORBIDDEN_ANALYTICS_IMPORTS:
            if forbidden in stripped:
                msg = f"{source} must not import forbidden symbol: {forbidden}"
                raise ValidationError(msg)


def _timestamp_column(
    frame: pl.DataFrame,
    *,
    basis: AnalyticsTimestampBasis,
) -> pl.Series:
    column = basis.value
    if column not in frame.columns:
        msg = f"timestamp basis column missing: {column}"
        raise ValidationError(msg)
    return frame[column]


def _with_rth_membership(
    frame: pl.DataFrame,
    *,
    basis: AnalyticsTimestampBasis,
) -> pl.DataFrame:
    timestamps = _timestamp_column(frame, basis=basis)
    resolved = CmeEsRthSessionResolver().resolve(timestamps)
    membership = [
        "RTH" if session_id == ES_RTH_SESSION_ID else "OUTSIDE_RTH"
        for session_id in resolved["session_id"].to_list()
    ]
    return frame.with_columns(pl.Series("rth_membership", membership))


def _with_time_of_day(
    frame: pl.DataFrame,
    *,
    basis: AnalyticsTimestampBasis,
    bucket_minutes: int = 60,
) -> pl.DataFrame:
    if bucket_minutes != 60:
        msg = "spike MVP supports 60-minute buckets only"
        raise ValidationError(msg)
    ts_col = basis.value
    return frame.with_columns(
        pl.col(ts_col)
        .dt.convert_time_zone("America/New_York")
        .dt.truncate("1h")
        .dt.strftime("%H:00")
        .alias("time_of_day_bucket")
    )


def compute_grouped_summary(
    frame: pl.DataFrame,
    *,
    horizon_bars: int,
    dimension: GroupDimension,
    min_sample_size: int,
    timestamp_basis: AnalyticsTimestampBasis = AnalyticsTimestampBasis.AVAILABLE_AT,
) -> pl.DataFrame:
    """Return grouped summary rows for one dimension."""
    subset = frame.filter(pl.col("horizon_bars") == horizon_bars)
    if dimension is GroupDimension.HORIZON:
        working = subset.with_columns(pl.col("horizon_bars").cast(pl.String).alias("group_value"))
        group_col = "group_value"
    elif dimension is GroupDimension.RTH_MEMBERSHIP:
        working = _with_rth_membership(subset, basis=timestamp_basis)
        group_col = "rth_membership"
    elif dimension is GroupDimension.TIME_OF_DAY:
        working = _with_time_of_day(subset, basis=timestamp_basis)
        group_col = "time_of_day_bucket"
    elif dimension is GroupDimension.CONTEXT_MET:
        working = subset.with_columns(
            pl.col("context_met_at_available_at").cast(pl.String).alias("group_value")
        )
        group_col = "group_value"
    elif dimension is GroupDimension.CALENDAR_MONTH:
        ts = _timestamp_column(subset, basis=timestamp_basis)
        working = subset.with_columns(ts.dt.strftime("%Y-%m").alias("group_value"))
        group_col = "group_value"
    else:
        msg = f"unsupported group dimension: {dimension}"
        raise ValidationError(msg)

    rows: list[dict[str, Any]] = []
    for group_value in working[group_col].unique().sort().to_list():
        group_frame = working.filter(pl.col(group_col) == group_value)
        summary = compute_run_summary(
            group_frame, horizon_bars=horizon_bars, min_sample_size=min_sample_size
        ).row(0, named=True)
        rows.append(
            {
                "run_id": summary["run_id"],
                "research_scope": summary["research_scope"],
                "horizon_bars": summary["horizon_bars"],
                "group_dimension": dimension.value,
                "group_value": str(group_value),
                "sample_size_total": summary["sample_size_total"],
                "sample_size_complete": summary["sample_size_complete"],
                "sample_size_incomplete": summary["sample_size_incomplete"],
                "metrics_eligible": summary["metrics_eligible"],
                "forward_return_mean": summary["forward_return_mean"],
                "forward_return_median": summary["forward_return_median"],
                "hit_rate": summary["hit_rate"],
                "mfe_mean": summary["mfe_mean"],
                "mfe_median": summary["mfe_median"],
                "mae_mean": summary["mae_mean"],
                "mae_median": summary["mae_median"],
            }
        )
    return pl.DataFrame(rows)


def compute_conditional_comparison(
    frame: pl.DataFrame,
    *,
    horizon_bars: int,
) -> ConditionalComparisonRow:
    """Compare outcomes where context_met is true vs false."""
    subset = frame.filter(pl.col("horizon_bars") == horizon_bars)
    complete = OutcomeAnalyticsFilter.complete_only().filter_for_aggregates(subset)
    true_rows = complete.filter(pl.col("context_met_at_available_at"))
    false_rows = complete.filter(~pl.col("context_met_at_available_at"))

    true_metrics = aggregate_complete_metrics(true_rows)
    false_metrics = aggregate_complete_metrics(false_rows)

    def _delta(true_val: float | None, false_val: float | None) -> float | None:
        if true_val is None or false_val is None:
            return None
        return true_val - false_val

    run_id = str(subset.row(0, named=True)["run_id"]) if len(subset) else ""
    return ConditionalComparisonRow(
        run_id=run_id,
        horizon_bars=horizon_bars,
        context_true_sample_size=len(true_rows),
        context_false_sample_size=len(false_rows),
        forward_return_mean_true=true_metrics["forward_return_mean"],
        forward_return_mean_false=false_metrics["forward_return_mean"],
        forward_return_mean_delta=_delta(
            true_metrics["forward_return_mean"],
            false_metrics["forward_return_mean"],
        ),
        hit_rate_true=true_metrics["hit_rate"],
        hit_rate_false=false_metrics["hit_rate"],
        hit_rate_delta=_delta(true_metrics["hit_rate"], false_metrics["hit_rate"]),
    )


__all__ = [
    "AnalyticsTimestampBasis",
    "ConditionalComparisonRow",
    "GroupDimension",
    "OutcomeAnalyticsFilter",
    "assert_read_only_analytics_package",
    "assert_read_only_module",
    "build_analysis_frame",
    "compute_conditional_comparison",
    "compute_grouped_summary",
    "compute_run_summary",
]
