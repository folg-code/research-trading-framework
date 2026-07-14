"""Roll policy contracts for continuous futures materialization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.contracts.identity import validate_product_code

VOLUME_RTH_CLOSE_POLICY_SLUG = "volume-rth-close"
ROLL_SCHEDULE_BUILDER_VERSION = "roll-schedule-builder-v1"


class RollSwitchAt(StrEnum):
    """When a confirmed roll becomes active."""

    NEXT_SESSION_OPEN = "next_session_open"


@dataclass(frozen=True, slots=True)
class VolumeRthCloseRollPolicy:
    """Volume-based roll evaluated after RTH close."""

    product: str
    confirmation_sessions: int = 1
    switch_at: RollSwitchAt = RollSwitchAt.NEXT_SESSION_OPEN

    def __post_init__(self) -> None:
        normalized_product = validate_product_code(self.product)
        if normalized_product != self.product:
            object.__setattr__(self, "product", normalized_product)
        if self.confirmation_sessions < 1:
            msg = "confirmation_sessions must be at least 1"
            raise ValidationError(msg)

    @property
    def slug(self) -> str:
        return VOLUME_RTH_CLOSE_POLICY_SLUG
