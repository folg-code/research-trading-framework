"""Build Signal Research analytics Parquet tables for dashboard dual-write."""

from __future__ import annotations

from collections.abc import Mapping

import polars as pl

from trading_framework.application.signal_research.analyze_signal_research import (
    AnalyzeSignalResearchResult,
)

# Canonical table names under analytics/*.parquet (D-S028-04).
# ``summary_metrics`` is the dashboard-facing name for run-level summary rows.
SIGNAL_ANALYTICS_PARQUET_TABLE_NAMES = frozenset(
    {
        "summary_metrics",
        "grouped_summaries",
        "conditional_comparison",
        "distribution_summaries",
        "join_diagnostics",
        "metric_histograms",
        "quality_warnings",
    }
)


def signal_analytics_parquet_tables(
    analytics: AnalyzeSignalResearchResult,
) -> dict[str, pl.DataFrame]:
    """Map one analytics result to named Parquet tables (omit empty optionals)."""
    tables: dict[str, pl.DataFrame] = {
        "summary_metrics": analytics.run_summaries,
        "distribution_summaries": analytics.distribution_summaries,
        "join_diagnostics": analytics.join_diagnostics,
        "quality_warnings": _quality_warnings_frame(analytics),
    }
    if analytics.grouped_summaries is not None:
        tables["grouped_summaries"] = analytics.grouped_summaries
    if analytics.conditional_comparison is not None:
        tables["conditional_comparison"] = analytics.conditional_comparison
    if analytics.metric_histograms is not None:
        tables["metric_histograms"] = analytics.metric_histograms
    return tables


def _quality_warnings_frame(analytics: AnalyzeSignalResearchResult) -> pl.DataFrame:
    rows = [
        {
            "code": warning.code.value if hasattr(warning.code, "value") else str(warning.code),
            "message": warning.message,
            "horizon_bars": warning.horizon_bars,
        }
        for warning in analytics.quality_warnings
    ]
    if not rows:
        return pl.DataFrame(
            schema={
                "code": pl.Utf8,
                "message": pl.Utf8,
                "horizon_bars": pl.Int64,
            }
        )
    return pl.DataFrame(rows)


def require_known_analytics_table_names(tables: Mapping[str, pl.DataFrame]) -> None:
    """Reject unknown analytics table names so dashboard contracts stay stable."""
    unknown = set(tables) - SIGNAL_ANALYTICS_PARQUET_TABLE_NAMES
    if unknown:
        msg = f"unknown signal analytics parquet tables: {sorted(unknown)}"
        raise ValueError(msg)
