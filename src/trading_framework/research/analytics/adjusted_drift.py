"""Sample-size-weighted shrinkage of forward-drift group means.

Phase 18, 18B Milestone 1 (Sprint 073) / D-P18B-03. No shrinkage/
empirical-Bayes precedent existed anywhere in this codebase before this
module. Computed once here, in the research/analytics layer -- the
dashboard applies no further shrinkage, per the vision doc's explicit
rule.
"""

from __future__ import annotations

import polars as pl

#: Reuses this project's own existing Signal Research interpretability
#: threshold (``DEFAULT_INTERPRETATION_MIN_SAMPLE_SIZE``) as the shrinkage
#: prior strength, rather than a new, unrelated constant (D-P18B-03). A
#: group shrinks roughly half-way toward the run's global mean at exactly
#: the sample size this codebase already calls "not yet reliably
#: interpretable".
DEFAULT_SHRINKAGE_PRIOR_STRENGTH = 100

ADJUSTED_FORWARD_DRIFT_SCHEMA_VERSION = "signal_research_adjusted_forward_drift.v1"


def adjusted_forward_drift_schema() -> dict[str, pl.DataType]:
    return {
        "schema_version": pl.String(),
        "run_id": pl.String(),
        "horizon_bars": pl.Int64(),
        "group_dimension": pl.String(),
        "group_value": pl.String(),
        "sample_size_complete": pl.Int64(),
        "forward_return_mean": pl.Float64(),
        "global_forward_return_mean": pl.Float64(),
        "shrinkage_weight": pl.Float64(),
        "adjusted_forward_return_mean": pl.Float64(),
    }


def empty_adjusted_forward_drift_dataframe() -> pl.DataFrame:
    return pl.DataFrame(schema=adjusted_forward_drift_schema())


def compute_adjusted_forward_drift(
    *,
    run_id: str,
    grouped_summaries: pl.DataFrame,
    summary_metrics: pl.DataFrame,
    prior_strength: int = DEFAULT_SHRINKAGE_PRIOR_STRENGTH,
) -> pl.DataFrame:
    """Shrink each (context, horizon) group's mean toward the run's global mean.

    ``adjusted_mean = (n * group_mean + k * global_mean) / (n + k)``, with
    ``n = sample_size_complete`` and ``k = prior_strength``. A group with
    ``n >> k`` stays close to its own raw mean; a group with ``n << k``
    shrinks close to the run's global (ungrouped) forward-return mean at
    the same horizon. ``shrinkage_weight = n / (n + k)`` is persisted
    alongside for transparency -- 1.0 means "no shrinkage applied",
    0.0 means "fully replaced by the global mean".

    A run with no grouped summaries or no summary metrics for a given
    horizon produces an empty table for that horizon, not a fabricated
    value.
    """
    if grouped_summaries.height == 0 or summary_metrics.height == 0:
        return empty_adjusted_forward_drift_dataframe()

    global_means = summary_metrics.select("horizon_bars", "forward_return_mean").rename(
        {"forward_return_mean": "global_forward_return_mean"}
    )
    joined = grouped_summaries.join(global_means, on="horizon_bars", how="inner")
    if joined.height == 0:
        return empty_adjusted_forward_drift_dataframe()

    result = joined.with_columns(
        (pl.col("sample_size_complete") / (pl.col("sample_size_complete") + prior_strength)).alias(
            "shrinkage_weight"
        )
    ).with_columns(
        (
            pl.col("shrinkage_weight") * pl.col("forward_return_mean")
            + (1 - pl.col("shrinkage_weight")) * pl.col("global_forward_return_mean")
        ).alias("adjusted_forward_return_mean")
    )
    return result.select(
        pl.lit(ADJUSTED_FORWARD_DRIFT_SCHEMA_VERSION).alias("schema_version"),
        pl.lit(run_id).alias("run_id"),
        pl.col("horizon_bars"),
        pl.col("group_dimension"),
        pl.col("group_value"),
        pl.col("sample_size_complete"),
        pl.col("forward_return_mean"),
        pl.col("global_forward_return_mean"),
        pl.col("shrinkage_weight"),
        pl.col("adjusted_forward_return_mean"),
    )
