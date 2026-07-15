"""Compare analytics summaries across model-family variants."""

from __future__ import annotations

import polars as pl

from trading_framework.application.signal_research.analyze_signal_research import (
    AnalyzeSignalResearchResult,
)
from trading_framework.research.analytics.schemas import (
    empty_family_comparison,
    validate_family_comparison,
)


def summarize_family_comparison(
    variant_results: tuple[tuple[str, str, AnalyzeSignalResearchResult], ...],
    *,
    primary_horizon_bars: int | None = None,
) -> pl.DataFrame:
    """Build a tabular comparison across evaluated family variants."""
    if not variant_results:
        empty = empty_family_comparison()
        validate_family_comparison(empty)
        return empty

    horizon = primary_horizon_bars
    if horizon is None:
        _, _, first_result = variant_results[0]
        primary_row = first_result.run_summaries.sort("horizon_bars").row(0, named=True)
        horizon = int(str(primary_row["horizon_bars"]))

    rows: list[dict[str, object]] = []
    for variant_id, run_id, result in variant_results:
        summary = result.run_summaries.filter(pl.col("horizon_bars") == horizon)
        if summary.height == 0:
            continue
        row = summary.row(0, named=True)
        rows.append(
            {
                "variant_id": variant_id,
                "run_id": run_id,
                "horizon_bars": horizon,
                "sample_size_complete": int(str(row["sample_size_complete"])),
                "sample_size_total": int(str(row["sample_size_total"])),
                "metrics_eligible": bool(row["metrics_eligible"]),
                "forward_return_mean": row["forward_return_mean"],
                "forward_return_median": row["forward_return_median"],
                "hit_rate": row["hit_rate"],
                "mfe_mean": row["mfe_mean"],
                "mfe_median": row["mfe_median"],
                "mae_mean": row["mae_mean"],
                "mae_median": row["mae_median"],
                "quality_warning_count": len(result.quality_warnings),
            }
        )

    frame = pl.DataFrame(rows, schema=empty_family_comparison().schema)
    validate_family_comparison(frame)
    return frame
