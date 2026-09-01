"""Exit Model contracts for Strategy Research."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from trading_framework.core.exceptions import ValidationError


class ExitReason(StrEnum):
    """Why a simulated position was closed."""

    FIXED_BARS = "fixed_bars"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    MAX_BARS = "max_bars"


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


@runtime_checkable
class PriceBracketExit(Protocol):
    """Additive contract for exit models whose exit is price-driven.

    A price-triggered exit still satisfies ``ExitModel`` (its
    ``exit_bar_index`` reports the worst-case/timeout bar), but the
    simulator needs the raw stop/target/timeout fields to run the
    intrabar bracket check itself. This protocol is deliberately a thin
    structural read of plain attributes, not a method-based interface —
    the kernel reads these fields directly rather than calling back into
    the model.
    """

    @property
    def stop_loss_bps(self) -> float:
        """Adverse move, in basis points, that closes the position at a loss."""
        ...

    @property
    def take_profit_bps(self) -> float:
        """Favorable move, in basis points, that closes the position at a profit."""
        ...

    @property
    def max_bars(self) -> int:
        """Bars after the entry fill after which the position is closed regardless."""
        ...


@dataclass(frozen=True, slots=True)
class BracketExitModel:
    """Close the position on a stop-loss, a take-profit, or a bar timeout.

    Locked semantics (D-S048-04):

    - Same-bar ambiguity: if a bar's low reaches the stop AND its high
      reaches the target, THE STOP WINS. Always. No intrabar path
      reconstruction, no open-proximity heuristic, no config flag.
    - Fill price: a stop or target fills at its own trigger price, with
      the existing ``slippage_bps`` applied against the trade. The
      ``max_bars`` timeout keeps the next-bar-open convention, byte
      identical to the fixed-bars path.
    - Scan window: from the entry fill bar inclusive. A gap through the
      stop on the entry bar is a stop-out at the trigger price, not a
      skipped trade.
    - Offsets are basis points, not price points, so a strategy is
      portable across instruments and price levels.

    ``exit_bar_index`` reports the WORST-CASE exit — the ``max_bars``
    timeout — which is what makes this model still satisfy the pure
    bar-index ``ExitModel`` contract even though its real exit is
    price-driven. The simulator dispatches on ``PriceBracketExit`` to run
    the actual bracket check.
    """

    stop_loss_bps: float
    take_profit_bps: float
    max_bars: int
    exit_model_id: str = "bracket"

    def __post_init__(self) -> None:
        normalized = self.exit_model_id.strip()
        if not normalized:
            msg = "exit_model_id must be non-empty"
            raise ValidationError(msg)
        if normalized != self.exit_model_id:
            object.__setattr__(self, "exit_model_id", normalized)
        if self.stop_loss_bps <= 0:
            msg = "stop_loss_bps must be positive"
            raise ValidationError(msg)
        if self.take_profit_bps <= 0:
            msg = "take_profit_bps must be positive"
            raise ValidationError(msg)
        if self.max_bars < 1:
            msg = "max_bars must be at least 1"
            raise ValidationError(msg)

    def exit_bar_index(self, *, entry_fill_bar_index: int) -> int:
        if entry_fill_bar_index < 0:
            msg = "entry_fill_bar_index must be non-negative"
            raise ValidationError(msg)
        return entry_fill_bar_index + self.max_bars
