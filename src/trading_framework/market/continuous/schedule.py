"""Roll schedule domain types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.continuous.policy import VolumeRthCloseRollPolicy
from trading_framework.market.contracts.identity import (
    validate_contract_code,
    validate_product_code,
)

ROLL_SCHEDULE_SCHEMA_VERSION = "roll-schedule-v1"


@final
@dataclass(frozen=True, slots=True)
class RollScheduleEntry:
    """One contiguous active-contract segment in a roll schedule."""

    product: str
    valid_from_session: date
    valid_to_session: date
    active_contract: str
    rule: str
    evidence_volume: int
    roll_id: str

    def __post_init__(self) -> None:
        normalized_product = validate_product_code(self.product)
        normalized_contract = validate_contract_code(self.active_contract)
        if normalized_product != self.product:
            object.__setattr__(self, "product", normalized_product)
        if normalized_contract != self.active_contract:
            object.__setattr__(self, "active_contract", normalized_contract)
        if self.valid_to_session < self.valid_from_session:
            msg = "valid_to_session must not be before valid_from_session"
            raise ValidationError(msg)
        if self.evidence_volume < 0:
            msg = "evidence_volume must be non-negative"
            raise ValidationError(msg)
        if not self.roll_id.strip():
            msg = "roll_id must be non-empty"
            raise ValidationError(msg)


@final
@dataclass(frozen=True, slots=True)
class RollSchedule:
    """Versioned roll schedule for one product and policy."""

    product: str
    policy: VolumeRthCloseRollPolicy
    version: int
    entries: tuple[RollScheduleEntry, ...]

    def __post_init__(self) -> None:
        normalized_product = validate_product_code(self.product)
        if normalized_product != self.product:
            object.__setattr__(self, "product", normalized_product)
        if self.policy.product != self.product:
            msg = "policy product must match schedule product"
            raise ValidationError(msg)
        if self.version < 1:
            msg = "roll schedule version must be at least 1"
            raise ValidationError(msg)
        if not self.entries:
            msg = "roll schedule must contain at least one entry"
            raise ValidationError(msg)

    def active_contract_for_session(self, session_date: date) -> str | None:
        """Return the active contract for ``session_date`` when covered by the schedule."""
        for entry in self.entries:
            if entry.valid_from_session <= session_date <= entry.valid_to_session:
                return entry.active_contract
        return None
