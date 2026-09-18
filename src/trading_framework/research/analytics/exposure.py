"""Notional exposure / equity ratio for a persisted Strategy Research run.

Phase 18, 18A Milestone 1a (Sprint 068) / D-P18-05. Computed purely
post-hoc from already-persisted ``trades.parquet`` and ``equity.parquet``
-- no simulator rerun, no margin/leverage model (the simulator has none;
this is the only exposure measure available). No new raw data.
"""

from __future__ import annotations

import polars as pl

EXPOSURE_SCHEMA_VERSION = "strategy_research_exposure.v1"


def exposure_schema() -> dict[str, pl.DataType]:
    return {
        "schema_version": pl.String(),
        "run_id": pl.String(),
        "observed_at": pl.Datetime(time_unit="us", time_zone="UTC"),
        "notional_exposure": pl.Float64(),
        "exposure_ratio": pl.Float64(),
    }


def empty_exposure_dataframe() -> pl.DataFrame:
    return pl.DataFrame(schema=exposure_schema())


def compute_exposure(*, run_id: str, trades: pl.DataFrame, equity: pl.DataFrame) -> pl.DataFrame:
    """Notional exposure and exposure/equity ratio on the equity observation grid.

    ``notional_exposure`` at a bar is ``sum(quantity * entry_fill_price)``
    over every trade open at that bar, half-open on
    ``[entry_fill_at, exit_fill_at)``. ``exposure_ratio`` is
    ``notional_exposure / equity`` at the same bar, ``null`` (never
    ``inf``/``NaN``) when equity is zero or negative.
    """
    if equity.height == 0:
        return empty_exposure_dataframe()

    equity_sorted = equity.sort("observed_at")

    if trades.height == 0:
        return equity_sorted.select(
            pl.lit(EXPOSURE_SCHEMA_VERSION).alias("schema_version"),
            pl.lit(run_id).alias("run_id"),
            pl.col("observed_at"),
            pl.lit(0.0).alias("notional_exposure"),
            pl.when(pl.col("equity") > 0)
            .then(0.0)
            .otherwise(None)
            .cast(pl.Float64)
            .alias("exposure_ratio"),
        )

    notional = pl.col("quantity") * pl.col("entry_fill_price")
    entries = trades.select(
        pl.col("entry_fill_at").alias("event_at"),
        notional.alias("delta"),
    )
    exits = trades.select(
        pl.col("exit_fill_at").alias("event_at"),
        (-notional).alias("delta"),
    )
    events = (
        pl.concat([entries, exits])
        .sort("event_at")
        .with_columns(pl.col("delta").cum_sum().alias("cumulative_notional"))
        .select("event_at", "cumulative_notional")
    )

    merged = equity_sorted.join_asof(
        events,
        left_on="observed_at",
        right_on="event_at",
        strategy="backward",
    ).with_columns(pl.col("cumulative_notional").fill_null(0.0).alias("notional_exposure"))

    return merged.select(
        pl.lit(EXPOSURE_SCHEMA_VERSION).alias("schema_version"),
        pl.lit(run_id).alias("run_id"),
        pl.col("observed_at"),
        pl.col("notional_exposure"),
        pl.when(pl.col("equity") > 0)
        .then(pl.col("notional_exposure") / pl.col("equity"))
        .otherwise(None)
        .cast(pl.Float64)
        .alias("exposure_ratio"),
    )
