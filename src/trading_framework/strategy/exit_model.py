"""Exit Model contracts for Strategy Research."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from trading_framework.core.exceptions import ValidationError


class ExitReason(StrEnum):
    """Why a simulated position was closed."""

    FIXED_BARS = "fixed_bars"


@runtime_checkable
class ExitModel(Protocol):
    """Contract for deterministic position exit rules."""

    @property
    def exit_model_id(self) -> str:
        """Stable identifier for this exit model definition."""
        ...

    def exit_bar_index(self, *, entry_fill_bar_index: int) -> int:
        """Bar index where the exit signal is emitted (before fill policy)."""
        ...


@dataclass(frozen=True, slots=True)
class FixedBarsExitModel:
    """Close the position a fixed number of bars after the entry fill bar."""

    exit_after_bars: int
    exit_model_id: str = "fixed_bars"

    def __post_init__(self) -> None:
        normalized = self.exit_model_id.strip()
        if not normalized:
            msg = "exit_model_id must be non-empty"
            raise ValidationError(msg)
        if normalized != self.exit_model_id:
            object.__setattr__(self, "exit_model_id", normalized)
        if self.exit_after_bars < 1:
            msg = "exit_after_bars must be at least 1"
            raise ValidationError(msg)

    def exit_bar_index(self, *, entry_fill_bar_index: int) -> int:
        if entry_fill_bar_index < 0:
            msg = "entry_fill_bar_index must be non-negative"
            raise ValidationError(msg)
        return entry_fill_bar_index + self.exit_after_bars

    @property
    def default_exit_reason(self) -> ExitReason:
        return ExitReason.FIXED_BARS
