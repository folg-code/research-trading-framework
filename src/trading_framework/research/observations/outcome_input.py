"""Adapt market model observations for the forward outcome calculator."""

from __future__ import annotations

import polars as pl

from trading_framework.signal_model.definitions import SignalDirection

_MARKET_OBSERVATION_OUTCOME_DIRECTION = SignalDirection.LONG.value


def observations_as_outcome_occurrences(observations: pl.DataFrame) -> pl.DataFrame:
    """Map market observations to occurrence-shaped rows for outcome calculation.

    Market-only research uses unsigned price movement with LONG normalization as the
    descriptive default (not a trading direction).
    """
    if len(observations) == 0:
        return pl.DataFrame(
            schema={
                "occurrence_id": pl.String(),
                "detected_at": pl.Datetime(time_unit="us", time_zone="UTC"),
                "available_at": pl.Datetime(time_unit="us", time_zone="UTC"),
                "reference_price": pl.Float64(),
                "direction": pl.String(),
            }
        )

    return observations.select(
        pl.col("observation_id").alias("occurrence_id"),
        pl.col("detected_at"),
        pl.col("available_at"),
        pl.col("reference_price"),
        pl.lit(_MARKET_OBSERVATION_OUTCOME_DIRECTION).alias("direction"),
    )
