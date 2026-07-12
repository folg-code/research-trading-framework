"""Spike-only Signal Research analytics helpers (S010 Wave 0).

Promoted to ``research/analytics/`` in Wave 1. Must not import model evaluation,
materialization or outcome calculator modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.signal_research import SignalResearchRunEnvelope
from trading_framework.research.outcomes.definition import OutcomeStatus
from trading_framework.research.scope import ResearchScope
from trading_framework.time.sessions import CmeEsRthSessionResolver
from trading_framework.time.sessions.constants import ES_RTH_SESSION_ID

ENTITY_KIND_SIGNAL = "SIGNAL_OCCURRENCE"
ENTITY_KIND_OBSERVATION = "MARKET_MODEL_OBSERVATION"

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


class AnalyticsTimestampBasis(StrEnum):
    AVAILABLE_AT = "available_at"
    DETECTED_AT = "detected_at"


class GroupDimension(StrEnum):
    HORIZON = "horizon"
    RTH_MEMBERSHIP = "rth_membership"
    TIME_OF_DAY = "time_of_day"
    CALENDAR_MONTH = "calendar_month"
    CONTEXT_MET = "context_met"


@dataclass(frozen=True, slots=True)
class RunSummaryRow:
    run_id: str
    research_scope: str
    horizon_bars: int
    sample_size_total: int
    sample_size_complete: int
    sample_size_incomplete: int
    completion_rate: float
    minimum_required: int
    metrics_eligible: bool
    forward_return_mean: float | None
    forward_return_median: float | None
    hit_rate: float | None
    mfe_mean: float | None
    mfe_median: float | None
    mae_mean: float | None
    mae_median: float | None


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


def assert_read_only_module(source_text: str) -> None:
    """Fail if spike analytics module imports forbidden compute paths."""
    for line in source_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(("import ", "from ")):
            continue
        for forbidden in FORBIDDEN_ANALYTICS_IMPORTS:
            if forbidden in stripped:
                msg = f"analytics spike must not import forbidden symbol: {forbidden}"
                raise ValidationError(msg)


def build_analysis_frame(envelope: SignalResearchRunEnvelope) -> pl.DataFrame:
    """Join persisted facts into one normalized analytics frame."""
    scope = envelope.manifest.effective_scope()
    outcomes = envelope.outcomes
    run_id = envelope.manifest.run_id
    research_scope = scope.value

    if scope is ResearchScope.SIGNAL_MODEL_ONLY:
        entities = envelope.occurrences.select(
            "occurrence_id",
            pl.lit(ENTITY_KIND_SIGNAL).alias("entity_kind"),
            "detected_at",
            "available_at",
            "reference_price",
            "instrument",
        )
        joined = outcomes.join(entities, on="occurrence_id", how="left")
        context_expr = pl.lit(None, dtype=pl.Boolean).alias("context_met_at_available_at")
    elif scope is ResearchScope.MARKET_MODEL_ONLY:
        entities = envelope.observations.select(
            pl.col("observation_id").alias("occurrence_id"),
            pl.lit(ENTITY_KIND_OBSERVATION).alias("entity_kind"),
            "detected_at",
            "available_at",
            "reference_price",
            "instrument",
        )
        joined = outcomes.join(entities, on="occurrence_id", how="left")
        context_expr = pl.lit(None, dtype=pl.Boolean).alias("context_met_at_available_at")
    elif scope is ResearchScope.MARKET_AND_SIGNAL:
        entities = envelope.occurrences.select(
            "occurrence_id",
            pl.lit(ENTITY_KIND_SIGNAL).alias("entity_kind"),
            "detected_at",
            "available_at",
            "reference_price",
            "instrument",
        )
        context = envelope.context.select("occurrence_id", "context_met_at_available_at")
        joined = outcomes.join(entities, on="occurrence_id", how="left").join(
            context,
            on="occurrence_id",
            how="left",
        )
        context_expr = pl.col("context_met_at_available_at")
    else:
        msg = f"unsupported research scope: {scope}"
        raise ValidationError(msg)

    return joined.select(
        pl.lit(run_id).alias("run_id"),
        pl.lit(research_scope).alias("research_scope"),
        pl.col("occurrence_id").alias("entity_id"),
        pl.col("entity_kind"),
        pl.col("horizon_bars"),
        pl.col("outcome_status"),
        pl.col("forward_return"),
        pl.col("mfe"),
        pl.col("mae"),
        pl.col("detected_at"),
        pl.col("available_at"),
        pl.col("reference_price"),
        pl.col("instrument"),
        context_expr,
    )


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


def _aggregate_complete_metrics(complete: pl.DataFrame) -> dict[str, float | None]:
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


def compute_run_summary(
    frame: pl.DataFrame,
    *,
    horizon_bars: int,
    min_sample_size: int,
) -> RunSummaryRow:
    """Aggregate one run x horizon summary."""
    subset = frame.filter(pl.col("horizon_bars") == horizon_bars)
    sample_total = len(subset)
    complete = subset.filter(pl.col("outcome_status") == OutcomeStatus.COMPLETE.value)
    sample_complete = len(complete)
    sample_incomplete = sample_total - sample_complete
    completion_rate = sample_complete / sample_total if sample_total else 0.0
    metrics_eligible = sample_complete >= min_sample_size

    metrics: dict[str, float | None]
    if metrics_eligible:
        metrics = _aggregate_complete_metrics(complete)
    else:
        metrics = {
            "forward_return_mean": None,
            "forward_return_median": None,
            "hit_rate": None,
            "mfe_mean": None,
            "mfe_median": None,
            "mae_mean": None,
            "mae_median": None,
        }

    run_id = str(subset.row(0, named=True)["run_id"]) if sample_total else ""
    scope = str(subset.row(0, named=True)["research_scope"]) if sample_total else ""
    return RunSummaryRow(
        run_id=run_id,
        research_scope=scope,
        horizon_bars=horizon_bars,
        sample_size_total=sample_total,
        sample_size_complete=sample_complete,
        sample_size_incomplete=sample_incomplete,
        completion_rate=completion_rate,
        minimum_required=min_sample_size,
        metrics_eligible=metrics_eligible,
        forward_return_mean=metrics["forward_return_mean"],
        forward_return_median=metrics["forward_return_median"],
        hit_rate=metrics["hit_rate"],
        mfe_mean=metrics["mfe_mean"],
        mfe_median=metrics["mfe_median"],
        mae_mean=metrics["mae_mean"],
        mae_median=metrics["mae_median"],
    )


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
        )
        rows.append(
            {
                "run_id": summary.run_id,
                "research_scope": summary.research_scope,
                "horizon_bars": summary.horizon_bars,
                "group_dimension": dimension.value,
                "group_value": str(group_value),
                "sample_size_total": summary.sample_size_total,
                "sample_size_complete": summary.sample_size_complete,
                "sample_size_incomplete": summary.sample_size_incomplete,
                "metrics_eligible": summary.metrics_eligible,
                "forward_return_mean": summary.forward_return_mean,
                "forward_return_median": summary.forward_return_median,
                "hit_rate": summary.hit_rate,
                "mfe_mean": summary.mfe_mean,
                "mfe_median": summary.mfe_median,
                "mae_mean": summary.mae_mean,
                "mae_median": summary.mae_median,
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
    complete = subset.filter(pl.col("outcome_status") == OutcomeStatus.COMPLETE.value)
    true_rows = complete.filter(pl.col("context_met_at_available_at"))
    false_rows = complete.filter(~pl.col("context_met_at_available_at"))

    true_metrics = _aggregate_complete_metrics(true_rows)
    false_metrics = _aggregate_complete_metrics(false_rows)

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
