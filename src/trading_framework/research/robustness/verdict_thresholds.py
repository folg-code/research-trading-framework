"""Verdict threshold contracts for robustness experiments."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from trading_framework.core.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class VerdictThresholds:
    """Explicit PASS / CONDITIONAL / FAIL gate thresholds."""

    min_stitched_oos_net_pnl: Decimal | None = None
    min_oos_beats_train_ratio: Decimal | None = None
    max_worst_stress_delta_net_pnl: Decimal | None = None
    max_mc_loss_probability: Decimal | None = None
    max_top_trades_concentration: Decimal | None = None
    fail_on_isolated_optima: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "fail_on_isolated_optima": self.fail_on_isolated_optima,
        }
        if self.min_stitched_oos_net_pnl is not None:
            payload["min_stitched_oos_net_pnl"] = str(self.min_stitched_oos_net_pnl)
        if self.min_oos_beats_train_ratio is not None:
            payload["min_oos_beats_train_ratio"] = str(self.min_oos_beats_train_ratio)
        if self.max_worst_stress_delta_net_pnl is not None:
            payload["max_worst_stress_delta_net_pnl"] = str(self.max_worst_stress_delta_net_pnl)
        if self.max_mc_loss_probability is not None:
            payload["max_mc_loss_probability"] = str(self.max_mc_loss_probability)
        if self.max_top_trades_concentration is not None:
            payload["max_top_trades_concentration"] = str(self.max_top_trades_concentration)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> VerdictThresholds:
        return cls(
            min_stitched_oos_net_pnl=_optional_decimal(payload.get("min_stitched_oos_net_pnl")),
            min_oos_beats_train_ratio=_optional_decimal(payload.get("min_oos_beats_train_ratio")),
            max_worst_stress_delta_net_pnl=_optional_decimal(
                payload.get("max_worst_stress_delta_net_pnl")
            ),
            max_mc_loss_probability=_optional_decimal(payload.get("max_mc_loss_probability")),
            max_top_trades_concentration=_optional_decimal(
                payload.get("max_top_trades_concentration")
            ),
            fail_on_isolated_optima=bool(payload.get("fail_on_isolated_optima", False)),
        )


def _optional_decimal(value: object | None) -> Decimal | None:
    if value is None:
        return None
    decimal_value = Decimal(str(value))
    if not decimal_value.is_finite():
        msg = "threshold must be a finite decimal"
        raise ValidationError(msg)
    return decimal_value
