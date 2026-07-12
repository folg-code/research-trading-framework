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
    expected = empty_analysis_frame()
    if frame.columns != expected.columns:
        msg = f"analysis frame columns mismatch: {frame.columns} != {expected.columns}"
        raise ValidationError(msg)
    for column, expected_dtype in expected.schema.items():
        actual_dtype = frame.schema.get(column)
        if actual_dtype != expected_dtype:
            msg = f"analysis frame dtype mismatch for {column}: {actual_dtype} != {expected_dtype}"
            raise ValidationError(msg)
