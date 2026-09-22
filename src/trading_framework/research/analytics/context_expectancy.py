"""Conditional trade expectancy by market context.

Phase 18, 18A Milestone 1b (Sprint 069) / D-P18-02. Generic over any
categorical Market Analysis component the run's Market Model expression
references -- not hardcoded to a named component or indicator.

The persisted Market Model result (``market_model_result_dataframe``) is a
single boolean gate column only; every intermediate component value is
discarded there. This module instead reads an already-assembled
``AnalysisFrame`` (built the same way ``evaluate_models`` already builds
one -- either the one already computed in-memory for a live run, or one
recomputed post-hoc for an existing run via ``run_analysis``) and selects
only the columns whose owning component is ``ComponentKind.STATE`` and is
actually referenced by the run's Market Model expression. Continuous
(``FEATURE``) or structural (``STRUCTURE``) components are never treated as
context, even if their dtype happens to be the same ``float64`` storage
type every component uses.
"""

from __future__ import annotations

import polars as pl

from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.research.analytics.market_model_context import state_context_aliases

CONTEXT_EXPECTANCY_SCHEMA_VERSION = "strategy_research_context_expectancy.v1"

DEFAULT_MIN_SAMPLE_SIZE = 5
DEFAULT_INTERPRETATION_MIN_SAMPLE_SIZE = 30


def context_expectancy_schema() -> dict[str, pl.DataType]:
    return {
        "schema_version": pl.String(),
        "run_id": pl.String(),
        "component_id": pl.String(),
        "label": pl.String(),
        "sample_count": pl.Int64(),
        "missing_context_count": pl.Int64(),
        "eligible": pl.Boolean(),
        "interpretable": pl.Boolean(),
        "net_pnl_mean": pl.Float64(),
        "net_pnl_median": pl.Float64(),
        "win_rate": pl.Float64(),
    }


def empty_context_expectancy_dataframe() -> pl.DataFrame:
    return pl.DataFrame(schema=context_expectancy_schema())


def compute_context_expectancy(
    *,
    run_id: str,
    market_model: MarketModelDefinition,
    frame: AnalysisFrame,
    trades: pl.DataFrame,
    registry: ComponentRegistry | None = None,
    min_sample_size: int = DEFAULT_MIN_SAMPLE_SIZE,
    interpretation_min_sample_size: int = DEFAULT_INTERPRETATION_MIN_SAMPLE_SIZE,
) -> pl.DataFrame:
    """Conditional net-PnL expectancy grouped by each qualifying context label.

    A run whose Market Model references no ``STATE``-kind component produces
    an empty table, not an error. ``missing_context_count`` counts trades
    whose ``entry_signal_at`` has no matching row on the frame's evaluation
    grid, shared across that component's label rows. Below
    ``min_sample_size`` a group's metric fields are null (not zero);
    between ``min_sample_size`` and ``interpretation_min_sample_size`` a
    group is computed but marked not ``interpretable``.
    """
    aliases = state_context_aliases(market_model=market_model, frame=frame, registry=registry)
    if not aliases or trades.height == 0:
        return empty_context_expectancy_dataframe()

    frame_df = pl.DataFrame(
        {"observed_at": list(frame.timestamps)}
        | {alias: list(frame.columns[alias]) for alias in aliases}
    )
    joined = trades.select("entry_signal_at", "net_pnl").join(
        frame_df, left_on="entry_signal_at", right_on="observed_at", how="left"
    )

    rows: list[dict[str, object]] = []
    for alias, component_id in aliases.items():
        missing_context_count = joined[alias].null_count()
        matched = joined.filter(pl.col(alias).is_not_null())
        if matched.height == 0:
            continue
        grouped = matched.group_by(alias).agg(
            pl.len().alias("sample_count"),
            pl.col("net_pnl").mean().alias("net_pnl_mean"),
            pl.col("net_pnl").median().alias("net_pnl_median"),
            (pl.col("net_pnl") > 0).mean().alias("win_rate"),
        )
        for group_row in grouped.to_dicts():
            sample_count = group_row["sample_count"]
            eligible = sample_count >= min_sample_size
            interpretable = sample_count >= interpretation_min_sample_size
            rows.append(
                {
                    "schema_version": CONTEXT_EXPECTANCY_SCHEMA_VERSION,
                    "run_id": run_id,
                    "component_id": component_id,
                    "label": str(group_row[alias]),
                    "sample_count": sample_count,
                    "missing_context_count": missing_context_count,
                    "eligible": eligible,
                    "interpretable": interpretable,
                    "net_pnl_mean": group_row["net_pnl_mean"] if eligible else None,
                    "net_pnl_median": group_row["net_pnl_median"] if eligible else None,
                    "win_rate": group_row["win_rate"] if eligible else None,
                }
            )

    if not rows:
        return empty_context_expectancy_dataframe()
    return pl.DataFrame(rows, schema=context_expectancy_schema())
