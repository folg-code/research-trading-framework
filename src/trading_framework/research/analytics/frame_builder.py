"""Scope-aware analysis frame builder for persisted Signal Research runs."""

from __future__ import annotations

from typing import assert_never

import polars as pl

from trading_framework.research.analytics.dimensions import (
    ENTITY_KIND_OBSERVATION,
    ENTITY_KIND_SIGNAL,
)
from trading_framework.research.analytics.schemas import validate_analysis_frame
from trading_framework.research.datasets.signal_research import SignalResearchRunEnvelope
from trading_framework.research.scope import ResearchScope


def build_analysis_frame(envelope: SignalResearchRunEnvelope) -> pl.DataFrame:
    """Join persisted facts into one normalized analytics frame.

    Responsibilities: scope-aware joins, column normalization and schema validation.
    No metric computation.
    """
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
        assert_never(scope)

    frame = joined.select(
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
    validate_analysis_frame(frame)
    return frame
