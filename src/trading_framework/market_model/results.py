"""Market Model evaluation results."""

import polars as pl


def market_model_result_dataframe(
    *,
    market_model_id: str,
    evaluation: pl.DataFrame,
) -> pl.DataFrame:
    """Materialize dense market model output on the evaluation grid."""
    return evaluation.select("timestamp", "available_at", "model_result").with_columns(
        pl.lit(market_model_id).alias("market_model_id")
    )
