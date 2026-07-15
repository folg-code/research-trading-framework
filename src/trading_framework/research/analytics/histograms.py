"""Metric histogram bins for Signal Research report charts."""

from __future__ import annotations

import polars as pl

from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.schemas import (
    empty_metric_histograms,
    validate_metric_histograms,
)

_DEFAULT_BIN_COUNT = 20
_METRICS = ("forward_return", "mfe", "mae")


def _bin_metric_values(values: pl.Series, *, bin_count: int) -> list[tuple[float, float, int]]:
    clean = values.drop_nulls()
    if clean.len() == 0:
        return []
    minimum = float(clean.min())  # type: ignore[arg-type]
    maximum = float(clean.max())  # type: ignore[arg-type]
    if minimum == maximum:
        return [(minimum, maximum, clean.len())]

    width = (maximum - minimum) / bin_count
    if width == 0:
        return [(minimum, maximum, clean.len())]

    counts = [0] * bin_count
    for value in clean:
        numeric = float(str(value))
        index = min(int((numeric - minimum) / width), bin_count - 1)
        counts[index] += 1

    bins: list[tuple[float, float, int]] = []
    for index, count in enumerate(counts):
        if count == 0:
            continue
        start = minimum + index * width
        end = minimum + (index + 1) * width
        bins.append((start, end, count))
    return bins


def compute_metric_histogram(
    frame: pl.DataFrame,
    *,
    horizon_bars: int,
    metric: str,
    outcome_filter: OutcomeAnalyticsFilter,
    bin_count: int = _DEFAULT_BIN_COUNT,
) -> pl.DataFrame:
    """Return histogram bin rows for one metric at one horizon."""
    subset = frame.filter(pl.col("horizon_bars") == horizon_bars)
    complete = outcome_filter.filter_for_aggregates(subset)
    run_id = str(subset.row(0, named=True)["run_id"]) if len(subset) else ""
    values = complete[metric]
    reference_mean = float(values.mean()) if len(complete) else None  # type: ignore[arg-type]
    reference_median = float(values.median()) if len(complete) else None  # type: ignore[arg-type]
    rows: list[dict[str, object]] = []
    for index, (start, end, count) in enumerate(_bin_metric_values(values, bin_count=bin_count)):
        rows.append(
            {
                "run_id": run_id,
                "horizon_bars": horizon_bars,
                "metric": metric,
                "bin_index": index,
                "bin_start": start,
                "bin_end": end,
                "count": count,
                "reference_mean": reference_mean,
                "reference_median": reference_median,
            }
        )
    histogram = pl.DataFrame(rows, schema=empty_metric_histograms().schema)
    validate_metric_histograms(histogram)
    return histogram


def summarize_metric_histograms(
    frame: pl.DataFrame,
    *,
    horizons: tuple[int, ...],
    outcome_filter: OutcomeAnalyticsFilter,
    bin_count: int = _DEFAULT_BIN_COUNT,
) -> pl.DataFrame:
    """Return histogram bins for forward return, MFE and MAE across horizons."""
    if not horizons:
        empty = empty_metric_histograms()
        validate_metric_histograms(empty)
        return empty

    parts: list[pl.DataFrame] = []
    for horizon in horizons:
        for metric in _METRICS:
            parts.append(
                compute_metric_histogram(
                    frame,
                    horizon_bars=horizon,
                    metric=metric,
                    outcome_filter=outcome_filter,
                    bin_count=bin_count,
                )
            )
    combined = pl.concat(parts) if parts else empty_metric_histograms()
    validate_metric_histograms(combined)
    return combined
