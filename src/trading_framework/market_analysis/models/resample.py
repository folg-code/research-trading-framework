"""Resampling specification for multitimeframe batch analysis."""

from dataclasses import dataclass

from trading_framework.core.exceptions import ValidationError
from trading_framework.time.models.timeframe import Timeframe

OHLCV_AGGREGATION_VERSION = "ohlcv_v1"


@dataclass(frozen=True, slots=True)
class ResampleSpec:
    """Fixed UTC OHLCV resampling semantics for Sprint 004 MVP."""

    target_timeframe: Timeframe
    timezone: str = "UTC"
    label: str = "left"
    closed: str = "left"
    aggregation_version: str = OHLCV_AGGREGATION_VERSION

    def __post_init__(self) -> None:
        if self.timezone != "UTC":
            msg = "Sprint 004 MVP supports UTC timezone only"
            raise ValidationError(msg)
        if self.label != "left" or self.closed != "left":
            msg = "Sprint 004 MVP supports left-labeled closed-left buckets only"
            raise ValidationError(msg)
        normalized_version = self.aggregation_version.strip()
        if not normalized_version:
            msg = "aggregation_version must be non-empty"
            raise ValidationError(msg)
        if normalized_version != self.aggregation_version:
            object.__setattr__(self, "aggregation_version", normalized_version)

    def to_json_dict(self) -> dict[str, str]:
        return {
            "target_timeframe": self.target_timeframe.value,
            "timezone": self.timezone,
            "label": self.label,
            "closed": self.closed,
            "aggregation_version": self.aggregation_version,
        }
