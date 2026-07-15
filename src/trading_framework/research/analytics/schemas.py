"""Validated Polars schemas for Signal Research analytics outputs."""

from __future__ import annotations

import polars as pl

from trading_framework.core.exceptions import ValidationError


def _analysis_frame_schema() -> dict[str, pl.DataType]:
    return {
        "run_id": pl.String(),
        "research_scope": pl.String(),
        "entity_id": pl.String(),
        "entity_kind": pl.String(),
        "horizon_bars": pl.Int64(),
        "outcome_status": pl.String(),
        "forward_return": pl.Float64(),
        "mfe": pl.Float64(),
        "mae": pl.Float64(),
        "detected_at": pl.Datetime(time_unit="us", time_zone="UTC"),
        "available_at": pl.Datetime(time_unit="us", time_zone="UTC"),
        "reference_price": pl.Float64(),
        "instrument": pl.String(),
        "context_met_at_available_at": pl.Boolean(),
    }


def empty_analysis_frame() -> pl.DataFrame:
    """Return an empty normalized analysis frame with the canonical schema."""
    return pl.DataFrame(schema=_analysis_frame_schema())


def validate_analysis_frame(frame: pl.DataFrame) -> None:
    """Validate normalized analysis frame columns and dtypes."""
    _validate_frame_schema(frame, expected=empty_analysis_frame(), label="analysis frame")


def _run_summary_schema() -> dict[str, pl.DataType]:
    return {
        "run_id": pl.String(),
        "research_scope": pl.String(),
        "horizon_bars": pl.Int64(),
        "sample_size_total": pl.Int64(),
        "sample_size_complete": pl.Int64(),
        "sample_size_incomplete": pl.Int64(),
        "completion_rate": pl.Float64(),
        "minimum_required": pl.Int64(),
        "metrics_eligible": pl.Boolean(),
        "forward_return_mean": pl.Float64(),
        "forward_return_median": pl.Float64(),
        "hit_rate": pl.Float64(),
        "mfe_mean": pl.Float64(),
        "mfe_median": pl.Float64(),
        "mae_mean": pl.Float64(),
        "mae_median": pl.Float64(),
    }


def empty_run_summaries() -> pl.DataFrame:
    """Return an empty RunSummary table with the canonical schema."""
    return pl.DataFrame(schema=_run_summary_schema())


def validate_run_summaries(frame: pl.DataFrame) -> None:
    """Validate RunSummary output columns and dtypes."""
    _validate_frame_schema(frame, expected=empty_run_summaries(), label="run summaries")


def _grouped_summary_schema() -> dict[str, pl.DataType]:
    return {
        "run_id": pl.String(),
        "research_scope": pl.String(),
        "horizon_bars": pl.Int64(),
        "group_dimension": pl.String(),
        "group_value": pl.String(),
        "sample_size_total": pl.Int64(),
        "sample_size_complete": pl.Int64(),
        "sample_size_incomplete": pl.Int64(),
        "metrics_eligible": pl.Boolean(),
        "forward_return_mean": pl.Float64(),
        "forward_return_median": pl.Float64(),
        "hit_rate": pl.Float64(),
        "mfe_mean": pl.Float64(),
        "mfe_median": pl.Float64(),
        "mae_mean": pl.Float64(),
        "mae_median": pl.Float64(),
    }


def empty_grouped_summaries() -> pl.DataFrame:
    """Return an empty GroupedSummary table with the canonical schema."""
    return pl.DataFrame(schema=_grouped_summary_schema())


def validate_grouped_summaries(frame: pl.DataFrame) -> None:
    """Validate GroupedSummary output columns and dtypes."""
    _validate_frame_schema(frame, expected=empty_grouped_summaries(), label="grouped summaries")


def _conditional_comparison_schema() -> dict[str, pl.DataType]:
    return {
        "run_id": pl.String(),
        "horizon_bars": pl.Int64(),
        "context_true_sample_size": pl.Int64(),
        "context_false_sample_size": pl.Int64(),
        "context_missing_sample_size": pl.Int64(),
        "comparison_status": pl.String(),
        "status_reason": pl.String(),
        "forward_return_mean_true": pl.Float64(),
        "forward_return_mean_false": pl.Float64(),
        "forward_return_mean_delta": pl.Float64(),
        "forward_return_median_true": pl.Float64(),
        "forward_return_median_false": pl.Float64(),
        "forward_return_median_delta": pl.Float64(),
        "hit_rate_true": pl.Float64(),
        "hit_rate_false": pl.Float64(),
        "hit_rate_delta": pl.Float64(),
        "mfe_mean_true": pl.Float64(),
        "mfe_mean_false": pl.Float64(),
        "mfe_mean_delta": pl.Float64(),
        "mfe_median_true": pl.Float64(),
        "mfe_median_false": pl.Float64(),
        "mfe_median_delta": pl.Float64(),
        "mae_mean_true": pl.Float64(),
        "mae_mean_false": pl.Float64(),
        "mae_mean_delta": pl.Float64(),
        "mae_median_true": pl.Float64(),
        "mae_median_false": pl.Float64(),
        "mae_median_delta": pl.Float64(),
    }


def empty_conditional_comparison() -> pl.DataFrame:
    """Return an empty ConditionalComparison table with the canonical schema."""
    return pl.DataFrame(schema=_conditional_comparison_schema())


def validate_conditional_comparison(frame: pl.DataFrame) -> None:
    """Validate ConditionalComparison output columns and dtypes."""
    _validate_frame_schema(
        frame,
        expected=empty_conditional_comparison(),
        label="conditional comparison",
    )


def _join_diagnostics_schema() -> dict[str, pl.DataType]:
    return {
        "run_id": pl.String(),
        "horizon_bars": pl.Int64(),
        "entity_count": pl.Int64(),
        "outcome_rows_total": pl.Int64(),
        "outcome_rows_complete": pl.Int64(),
        "outcome_rows_unmatched_entity": pl.Int64(),
        "matched_context_rows": pl.Int64(),
        "missing_context_rows": pl.Int64(),
        "duplicate_context_matches": pl.Int64(),
        "context_true_complete": pl.Int64(),
        "context_false_complete": pl.Int64(),
        "context_missing_complete": pl.Int64(),
        "overlapping_outcome_windows": pl.Int64(),
        "overlapping_outcome_rate": pl.Float64(),
    }


def empty_join_diagnostics() -> pl.DataFrame:
    """Return an empty join diagnostics table with the canonical schema."""
    return pl.DataFrame(schema=_join_diagnostics_schema())


def validate_join_diagnostics(frame: pl.DataFrame) -> None:
    """Validate join diagnostics output columns and dtypes."""
    _validate_frame_schema(frame, expected=empty_join_diagnostics(), label="join diagnostics")


def _distribution_summaries_schema() -> dict[str, pl.DataType]:
    return {
        "run_id": pl.String(),
        "horizon_bars": pl.Int64(),
        "sample_size_complete": pl.Int64(),
        "minimum_required": pl.Int64(),
        "interpretation_minimum_required": pl.Int64(),
        "metrics_computable": pl.Boolean(),
        "metrics_interpretable": pl.Boolean(),
        "forward_return_p10": pl.Float64(),
        "forward_return_p25": pl.Float64(),
        "forward_return_p75": pl.Float64(),
        "forward_return_p90": pl.Float64(),
        "forward_return_std": pl.Float64(),
        "forward_return_min": pl.Float64(),
        "forward_return_max": pl.Float64(),
    }


def empty_distribution_summaries() -> pl.DataFrame:
    """Return an empty distribution summary table with the canonical schema."""
    return pl.DataFrame(schema=_distribution_summaries_schema())


def validate_distribution_summaries(frame: pl.DataFrame) -> None:
    """Validate distribution summary output columns and dtypes."""
    _validate_frame_schema(
        frame,
        expected=empty_distribution_summaries(),
        label="distribution summaries",
    )


def _metric_histograms_schema() -> dict[str, pl.DataType]:
    return {
        "run_id": pl.String(),
        "horizon_bars": pl.Int64(),
        "metric": pl.String(),
        "bin_index": pl.Int64(),
        "bin_start": pl.Float64(),
        "bin_end": pl.Float64(),
        "count": pl.Int64(),
        "reference_mean": pl.Float64(),
        "reference_median": pl.Float64(),
    }


def empty_metric_histograms() -> pl.DataFrame:
    """Return an empty metric histogram table with the canonical schema."""
    return pl.DataFrame(schema=_metric_histograms_schema())


def validate_metric_histograms(frame: pl.DataFrame) -> None:
    """Validate metric histogram output columns and dtypes."""
    _validate_frame_schema(
        frame,
        expected=empty_metric_histograms(),
        label="metric histograms",
    )


def _family_comparison_schema() -> dict[str, pl.DataType]:
    return {
        "variant_id": pl.String(),
        "run_id": pl.String(),
        "horizon_bars": pl.Int64(),
        "sample_size_complete": pl.Int64(),
        "sample_size_total": pl.Int64(),
        "metrics_eligible": pl.Boolean(),
        "forward_return_mean": pl.Float64(),
        "forward_return_median": pl.Float64(),
        "hit_rate": pl.Float64(),
        "mfe_mean": pl.Float64(),
        "mfe_median": pl.Float64(),
        "mae_mean": pl.Float64(),
        "mae_median": pl.Float64(),
        "quality_warning_count": pl.Int64(),
    }


def empty_family_comparison() -> pl.DataFrame:
    """Return an empty model-family comparison table with the canonical schema."""
    return pl.DataFrame(schema=_family_comparison_schema())


def validate_family_comparison(frame: pl.DataFrame) -> None:
    """Validate model-family comparison output columns and dtypes."""
    _validate_frame_schema(
        frame,
        expected=empty_family_comparison(),
        label="family comparison",
    )


def _validate_frame_schema(
    frame: pl.DataFrame,
    *,
    expected: pl.DataFrame,
    label: str,
) -> None:
    if frame.columns != expected.columns:
        msg = f"{label} columns mismatch: {frame.columns} != {expected.columns}"
        raise ValidationError(msg)
    for column, expected_dtype in expected.schema.items():
        actual_dtype = frame.schema.get(column)
        if actual_dtype != expected_dtype:
            msg = f"{label} dtype mismatch for {column}: {actual_dtype} != {expected_dtype}"
            raise ValidationError(msg)
