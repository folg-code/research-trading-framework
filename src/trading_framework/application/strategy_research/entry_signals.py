"""Build gated strategy entry signals from model evaluation outputs."""

from __future__ import annotations

import polars as pl


def build_gated_entry_signals(
    *,
    signal_emissions: pl.DataFrame,
    market_state: pl.DataFrame,
) -> pl.DataFrame:
    """Return sparse entry intents where both signal fired and market model is true."""
    return (
        signal_emissions.join(
            market_state.select("available_at", "model_result"),
            on="available_at",
            how="inner",
        )
        .filter(pl.col("model_result"))
        .select("available_at", "direction")
    )
