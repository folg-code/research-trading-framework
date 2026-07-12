"""Join and overlap diagnostics for Signal Research analytics."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import polars as pl

from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.schemas import (
    empty_join_diagnostics,
    validate_join_diagnostics,
)
from trading_framework.research.datasets.signal_research import SignalResearchRunEnvelope
from trading_framework.research.scope import ResearchScope
from trading_framework.time.models.timeframe import Timeframe


def _entity_count(envelope: SignalResearchRunEnvelope) -> int:
    scope = envelope.manifest.effective_scope()
    if scope is ResearchScope.MARKET_MODEL_ONLY:
        return len(envelope.observations)
    return len(envelope.occurrences)


def _context_table_diagnostics(envelope: SignalResearchRunEnvelope) -> dict[str, int]:
    scope = envelope.manifest.effective_scope()
    if scope is not ResearchScope.MARKET_AND_SIGNAL:
        return {
            "matched_context_rows": 0,
            "missing_context_rows": 0,
            "duplicate_context_matches": 0,
        }

    occurrence_ids = envelope.occurrences["occurrence_id"].to_list()
    context = envelope.context
    matched_ids = set(context["occurrence_id"].to_list())
    missing_context_rows = sum(1 for occ_id in occurrence_ids if occ_id not in matched_ids)
    duplicate_context_matches = (
        context.group_by("occurrence_id")
        .agg(pl.len().alias("match_count"))
        .filter(pl.col("match_count") > 1)
        .height
    )
    return {
        "matched_context_rows": len(context),
        "missing_context_rows": missing_context_rows,
        "duplicate_context_matches": duplicate_context_matches,
    }


def _count_overlapping_outcome_windows(
    complete: pl.DataFrame,
    *,
    horizon_bars: int,
    evaluation_timeframe: str,
) -> tuple[int, float]:
    if complete.height < 2:
        return 0, 0.0

    bar_seconds = Timeframe(evaluation_timeframe).total_seconds
    window = timedelta(seconds=horizon_bars * bar_seconds)
    timestamps = complete.sort("available_at")["available_at"].to_list()
    overlap_count = 0
    for index in range(len(timestamps) - 1):
        if timestamps[index + 1] < timestamps[index] + window:
            overlap_count += 1
    rate = overlap_count / (len(timestamps) - 1)
    return overlap_count, rate


def compute_join_diagnostics(
    envelope: SignalResearchRunEnvelope,
    frame: pl.DataFrame,
    *,
    horizons: tuple[int, ...],
    outcome_filter: OutcomeAnalyticsFilter,
    evaluation_timeframe: str,
) -> pl.DataFrame:
    """Return per-horizon join and context diagnostics for one analysis frame."""
    if not horizons:
        empty = empty_join_diagnostics()
        validate_join_diagnostics(empty)
        return empty

    context_diag = _context_table_diagnostics(envelope)
    entity_count = _entity_count(envelope)
    run_id = envelope.manifest.run_id
    rows: list[dict[str, Any]] = []

    for horizon in horizons:
        subset = frame.filter(pl.col("horizon_bars") == horizon)
        complete = outcome_filter.filter_for_aggregates(subset)
        unmatched_entity_rows = subset.filter(pl.col("detected_at").is_null()).height
        context_true = complete.filter(pl.col("context_met_at_available_at").eq(True)).height
        context_false = complete.filter(pl.col("context_met_at_available_at").eq(False)).height
        context_missing = complete.filter(pl.col("context_met_at_available_at").is_null()).height
        overlap_count, overlap_rate = _count_overlapping_outcome_windows(
            complete,
            horizon_bars=horizon,
            evaluation_timeframe=evaluation_timeframe,
        )
        rows.append(
            {
                "run_id": run_id,
                "horizon_bars": horizon,
                "entity_count": entity_count,
                "outcome_rows_total": subset.height,
                "outcome_rows_complete": complete.height,
                "outcome_rows_unmatched_entity": unmatched_entity_rows,
                "matched_context_rows": context_diag["matched_context_rows"],
                "missing_context_rows": context_diag["missing_context_rows"],
                "duplicate_context_matches": context_diag["duplicate_context_matches"],
                "context_true_complete": context_true,
                "context_false_complete": context_false,
                "context_missing_complete": context_missing,
                "overlapping_outcome_windows": overlap_count,
                "overlapping_outcome_rate": overlap_rate,
            }
        )

    diagnostics = pl.DataFrame(rows, schema=empty_join_diagnostics().schema)
    validate_join_diagnostics(diagnostics)
    return diagnostics
