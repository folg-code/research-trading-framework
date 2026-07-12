"""Tests for Signal Research analytics schemas."""

from __future__ import annotations

from datetime import UTC, datetime

import polars as pl
import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.analytics.schemas import (
    empty_analysis_frame,
    validate_analysis_frame,
)


def test_empty_analysis_frame_has_expected_columns() -> None:
    frame = empty_analysis_frame()
    assert "entity_id" in frame.columns
    assert "entity_kind" in frame.columns
    assert "context_met_at_available_at" in frame.columns


def test_validate_analysis_frame_rejects_extra_column() -> None:
    frame = empty_analysis_frame().with_columns(pl.lit("x").alias("extra"))
    with pytest.raises(ValidationError, match="columns mismatch"):
        validate_analysis_frame(frame)


def test_validate_analysis_frame_rejects_wrong_dtype() -> None:
    detected_at = datetime(2024, 1, 1, tzinfo=UTC)
    frame = pl.DataFrame(
        {
            "run_id": ["run-1"],
            "research_scope": ["signal_model_only"],
            "entity_id": ["occ-1"],
            "entity_kind": ["SIGNAL_OCCURRENCE"],
            "horizon_bars": ["5"],
            "outcome_status": ["complete"],
            "forward_return": [0.01],
            "mfe": [0.02],
            "mae": [-0.01],
            "detected_at": [detected_at],
            "available_at": [detected_at],
            "reference_price": [100.0],
            "instrument": ["TEST"],
            "context_met_at_available_at": [None],
        }
    )
    with pytest.raises(ValidationError, match="dtype mismatch"):
        validate_analysis_frame(frame)
