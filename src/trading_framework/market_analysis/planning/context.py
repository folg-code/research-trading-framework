"""Planning context for dependency resolution."""

from dataclasses import dataclass

from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.market_analysis.models.timeframes import resolve_evaluation_timeframe
from trading_framework.time.models.timeframe import Timeframe


@dataclass(frozen=True, slots=True)
class PlanningContext:
    """Immutable execution context shared by all nodes in one plan."""

    dataset_ref: DatasetRef
    timeframe: Timeframe
    requested_range: TimeRange
    evaluation_timeframe: Timeframe | None = None

    @property
    def source_timeframe(self) -> Timeframe:
        return self.timeframe

    def __post_init__(self) -> None:
        evaluation = self.evaluation_timeframe or self.timeframe
        if self.evaluation_timeframe is None:
            object.__setattr__(self, "evaluation_timeframe", evaluation)
        resolve_evaluation_timeframe(
            source_timeframe=self.timeframe,
            requested=evaluation,
        )
