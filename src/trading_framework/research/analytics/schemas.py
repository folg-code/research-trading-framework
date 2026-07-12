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
        "forward_return_mean_true": pl.Float64(),
        "forward_return_mean_false": pl.Float64(),
        "forward_return_mean_delta": pl.Float64(),
        "hit_rate_true": pl.Float64(),
        "hit_rate_false": pl.Float64(),
        "hit_rate_delta": pl.Float64(),
        "mfe_mean_true": pl.Float64(),
        "mfe_mean_false": pl.Float64(),
        "mfe_mean_delta": pl.Float64(),
        "mae_mean_true": pl.Float64(),
        "mae_mean_false": pl.Float64(),
        "mae_mean_delta": pl.Float64(),
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
