"""ContextFact — market model context evaluated at signal available_at."""

from __future__ import annotations

import polars as pl

from trading_framework.core.exceptions import ValidationError


def _context_schema() -> dict[str, pl.DataType]:
    return {
        "occurrence_id": pl.String(),
        "market_model_id": pl.String(),
        "context_met_at_available_at": pl.Boolean(),
        "context_evaluated_at": pl.Datetime(time_unit="us", time_zone="UTC"),
    }


def empty_context_facts_dataframe() -> pl.DataFrame:
    """Return an empty context fact table with the canonical schema."""
    return pl.DataFrame(schema=_context_schema())


def validate_context_facts_dataframe(frame: pl.DataFrame) -> None:
    """Validate context fact table columns."""
    expected = empty_context_facts_dataframe()
    if frame.columns != expected.columns:
        msg = f"context columns mismatch: {frame.columns} != {expected.columns}"
        raise ValidationError(msg)


def align_context_facts_at_available_at(
    occurrences: pl.DataFrame,
    market_state: pl.DataFrame,
    *,
    market_model_id: str,
) -> pl.DataFrame:
    """Join market model context to each occurrence at ``available_at``.

    Uses backward as-of semantics: latest market state legally available at the signal
    ``available_at`` timestamp.
    """
    if len(occurrences) == 0:
        return empty_context_facts_dataframe()

    state = market_state.select("available_at", "model_result").sort("available_at")
    sorted_occurrences = occurrences.sort("available_at")
    joined = sorted_occurrences.join_asof(
        state,
        on="available_at",
        strategy="backward",
    )
    return joined.select(
        pl.col("occurrence_id"),
        pl.lit(market_model_id).alias("market_model_id"),
        pl.col("model_result").alias("context_met_at_available_at"),
        pl.col("available_at").alias("context_evaluated_at"),
    )
