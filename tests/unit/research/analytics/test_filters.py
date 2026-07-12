"""Tests for Signal Research analytics filters."""

from __future__ import annotations

from datetime import UTC, datetime

import polars as pl
import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.outcomes.definition import OutcomeStatus


def test_complete_only_filters_complete_rows() -> None:
    frame = pl.DataFrame(
        {
            "outcome_status": [
                OutcomeStatus.COMPLETE.value,
                OutcomeStatus.INCOMPLETE_HORIZON.value,
            ],
            "forward_return": [0.01, 0.02],
        }
    )
    filtered = OutcomeAnalyticsFilter.complete_only().filter_for_aggregates(frame)
    assert filtered.height == 1
    assert filtered.row(0, named=True)["outcome_status"] == OutcomeStatus.COMPLETE.value


def test_outcome_analytics_filter_rejects_empty_status_set() -> None:
    with pytest.raises(ValidationError, match="aggregate_statuses must not be empty"):
        OutcomeAnalyticsFilter(aggregate_statuses=frozenset())


def test_outcome_analytics_filter_accepts_custom_statuses() -> None:
    detected_at = datetime(2024, 1, 1, tzinfo=UTC)
    frame = pl.DataFrame(
        {
            "outcome_status": [
                OutcomeStatus.COMPLETE.value,
                OutcomeStatus.INSUFFICIENT_DATA.value,
            ],
            "detected_at": [detected_at, detected_at],
        }
    )
    custom = OutcomeAnalyticsFilter(
        aggregate_statuses=frozenset({OutcomeStatus.COMPLETE, OutcomeStatus.INSUFFICIENT_DATA})
    )
    assert custom.filter_for_aggregates(frame).height == 2
