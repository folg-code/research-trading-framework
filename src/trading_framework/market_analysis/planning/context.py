"""Planning context for dependency resolution."""

from dataclasses import dataclass

from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.time.models.timeframe import Timeframe


@dataclass(frozen=True, slots=True)
class PlanningContext:
    """Immutable execution context shared by all nodes in one plan."""

    dataset_ref: DatasetRef
    timeframe: Timeframe
    requested_range: TimeRange
