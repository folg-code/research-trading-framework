"""Analysis execution context."""

from dataclasses import dataclass

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.time.models.timeframe import Timeframe


@dataclass(frozen=True, slots=True)
class AnalysisContext:
    """Immutable context for one analysis run."""

    dataset_ref: DatasetRef
    timeframe: Timeframe
    requested_range: TimeRange
    computation_range: TimeRange
    engine_version: str

    def __post_init__(self) -> None:
        normalized_engine_version = self.engine_version.strip()
        if not normalized_engine_version:
            msg = "engine_version must be non-empty"
            raise ValidationError(msg)
        if normalized_engine_version != self.engine_version:
            object.__setattr__(self, "engine_version", normalized_engine_version)

        if self.dataset_ref.dataset_id.timeframe != self.timeframe:
            msg = "context timeframe must match dataset timeframe in MVP"
            raise ValidationError(msg)

        if self.computation_range.start > self.requested_range.start:
            msg = "computation_range must start at or before requested_range"
            raise ValidationError(msg)
        if self.computation_range.end < self.requested_range.end:
            msg = "computation_range must end at or after requested_range"
            raise ValidationError(msg)
