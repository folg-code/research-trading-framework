"""Safety contracts for dry-run execution."""

from dataclasses import dataclass
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.execution.modes import ExecutionMode


@final
@dataclass(frozen=True, slots=True)
class ExecutionSafetyPolicy:
    """Safety policy that prevents real order submission in early execution increments."""

    mode: ExecutionMode
    allow_real_orders: bool = False
    allow_exchange_credentials: bool = False

    def __post_init__(self) -> None:
        if self.mode.value != ExecutionMode.DRY_RUN.value:
            msg = "only DRY_RUN execution mode is supported"
            raise ValidationError(msg)
        if self.allow_real_orders:
            msg = "dry-run execution must not allow real orders"
            raise ValidationError(msg)
        if self.allow_exchange_credentials:
            msg = "dry-run execution must not accept exchange credentials"
            raise ValidationError(msg)


DRY_RUN_SAFETY_POLICY = ExecutionSafetyPolicy(mode=ExecutionMode.DRY_RUN)
