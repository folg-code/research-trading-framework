"""Tests for conditional context comparison analytics."""

from __future__ import annotations

from datetime import UTC, datetime

import polars as pl

from trading_framework.research.analytics.conditional import (
    ConditionalComparisonStatus,
    compute_conditional_comparison,
)
from trading_framework.research.analytics.schemas import empty_analysis_frame
from trading_framework.research.outcomes.definition import OutcomeStatus


def _frame(*, context_values: list[bool | None]) -> pl.DataFrame:
    base = empty_analysis_frame()
    rows = []
    for index, context in enumerate(context_values):
        rows.append(
            {
                "run_id": "run-1",
                "research_scope": "market_and_signal",
                "entity_id": f"occ-{index}",
                "entity_kind": "signal",
                "horizon_bars": 5,
                "outcome_status": OutcomeStatus.COMPLETE.value,
                "forward_return": 0.001,
                "mfe": 0.002,
                "mae": -0.001,
                "detected_at": datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
                "available_at": datetime(2024, 1, 1, 12, 1, tzinfo=UTC),
                "reference_price": 100.0,
                "instrument": "TEST",
                "context_met_at_available_at": context,
            }
        )
    return pl.DataFrame(rows, schema=base.schema)


def test_conditional_comparison_excludes_unresolved_context_from_false_arm() -> None:
    frame = _frame(context_values=[None, False])
    comparison = compute_conditional_comparison(frame, horizon_bars=5).row(0, named=True)

    assert comparison["context_true_sample_size"] == 0
    assert comparison["context_false_sample_size"] == 1
    assert comparison["context_missing_sample_size"] == 1
    assert (
        comparison["comparison_status"]
        == ConditionalComparisonStatus.EMPTY_CONDITIONED_SAMPLE.value
    )


def test_conditional_comparison_reports_available_when_both_arms_present() -> None:
    frame = _frame(context_values=[True, False, None])
    comparison = compute_conditional_comparison(frame, horizon_bars=5).row(0, named=True)

    assert comparison["context_true_sample_size"] == 1
    assert comparison["context_false_sample_size"] == 1
    assert comparison["context_missing_sample_size"] == 1
    assert comparison["comparison_status"] == ConditionalComparisonStatus.AVAILABLE.value
    assert comparison["forward_return_mean_delta"] == 0.0
