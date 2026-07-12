"""Signal Model evaluation results."""

import polars as pl


def signal_model_condition_dataframe(
    *,
    signal_model_id: str,
    evaluation: pl.DataFrame,
) -> pl.DataFrame:
    """Materialize dense signal condition output on the evaluation grid."""
    return (
        evaluation.select("timestamp", "available_at", "model_result")
        .rename({"model_result": "condition_met"})
        .with_columns(pl.lit(signal_model_id).alias("signal_model_id"))
    )
