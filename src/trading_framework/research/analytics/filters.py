"""Outcome filters for Signal Research analytics aggregates."""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.outcomes.definition import OutcomeStatus


@dataclass(frozen=True, slots=True)
class OutcomeAnalyticsFilter:
    """Select outcome rows that contribute to aggregate metrics.

    Sample diagnostics always use the full analysis frame. Aggregate metrics apply
    this filter only.
    """

    aggregate_statuses: frozenset[OutcomeStatus]

    def __post_init__(self) -> None:
        if not self.aggregate_statuses:
            msg = "aggregate_statuses must not be empty"
            raise ValidationError(msg)

    @classmethod
    def complete_only(cls) -> OutcomeAnalyticsFilter:
        """MVP default — COMPLETE rows only for mean / median / hit rate / MFE / MAE."""
        return cls(aggregate_statuses=frozenset({OutcomeStatus.COMPLETE}))

    def filter_for_aggregates(self, frame: pl.DataFrame) -> pl.DataFrame:
        """Return rows eligible for aggregate metric computation."""
        allowed = {status.value for status in self.aggregate_statuses}
        return frame.filter(pl.col("outcome_status").is_in(list(allowed)))
