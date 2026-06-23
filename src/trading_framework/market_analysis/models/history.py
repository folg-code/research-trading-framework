"""Warm-up and history requirement models."""

from dataclasses import dataclass

from trading_framework.core.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class HistoryRequirement:
    """Number of additional bars required before the requested range start."""

    bars_before: int

    def __post_init__(self) -> None:
        if self.bars_before < 0:
            msg = "bars_before must be >= 0"
            raise ValidationError(msg)


@dataclass(frozen=True, slots=True)
class WarmUpMetadata:
    """Describes warm-up region excluded from the returned valid range."""

    warmup_bars: int
    valid_from_index: int
    valid_to_index: int

    def __post_init__(self) -> None:
        if self.warmup_bars < 0:
            msg = "warmup_bars must be >= 0"
            raise ValidationError(msg)
        if self.valid_from_index < 0:
            msg = "valid_from_index must be >= 0"
            raise ValidationError(msg)
        if self.valid_to_index < self.valid_from_index:
            msg = "valid_to_index must be >= valid_from_index"
            raise ValidationError(msg)
