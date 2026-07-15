"""Statistical diagnostics experiment contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from trading_framework.core.exceptions import ValidationError


class TimeBucketMode(StrEnum):
    """Temporal bucket granularity for stability metrics."""

    MONTH = "MONTH"
    QUARTER = "QUARTER"


@dataclass(frozen=True, slots=True)
class StatisticalDiagnosticsSpec:
    """Declared statistical diagnostics settings for one experiment."""

    time_bucket_mode: TimeBucketMode = TimeBucketMode.MONTH
    top_k_trades: int = 5
    top_k_days: int = 5
    parameter_overrides: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if self.top_k_trades <= 0:
            msg = "top_k_trades must be positive"
            raise ValidationError(msg)
        if self.top_k_days <= 0:
            msg = "top_k_days must be positive"
            raise ValidationError(msg)
        if self.parameter_overrides is None:
            object.__setattr__(self, "parameter_overrides", {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "time_bucket_mode": self.time_bucket_mode.value,
            "top_k_trades": self.top_k_trades,
            "top_k_days": self.top_k_days,
            "parameter_overrides": self.parameter_overrides,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> StatisticalDiagnosticsSpec:
        overrides_payload = payload.get("parameter_overrides", {})
        return cls(
            time_bucket_mode=TimeBucketMode(str(payload.get("time_bucket_mode", "MONTH"))),
            top_k_trades=int(payload.get("top_k_trades", 5)),
            top_k_days=int(payload.get("top_k_days", 5)),
            parameter_overrides={str(key): str(value) for key, value in overrides_payload.items()},
        )
