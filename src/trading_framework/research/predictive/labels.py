"""Label contracts for Predictive Research (D-S039-08, D-S039-17)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, assert_never

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.time.models.timeframe import Timeframe


class LabelKind(StrEnum):
    """How the single declared forward-return horizon becomes a learning target."""

    REGRESSION = "REGRESSION"
    BINARY = "BINARY"
    TERNARY = "TERNARY"


@dataclass(frozen=True, slots=True)
class LabelSpec:
    """Declared target derived from ``forward_return`` at one horizon.

    Horizon is a bar ``Timeframe`` (for example ``15m``), the same language as
    Signal Research YAML horizons. Conversion to
    ``ForwardOutcomeDefinition.horizon_bars`` happens at matrix-build time via
    ``horizon_to_bars`` against the study ``evaluation_timeframe``. Incomplete
    outcome rows are an exclusion policy on the builder, not a field here.

    ATR-adjusted regression (``forward_return / atr_at_entry``) is deferred
    (D-S039-17) and is not part of this contract.

    Kind semantics:

    * ``REGRESSION`` — target is ``forward_return`` at the horizon.
    * ``BINARY`` — ``1`` if ``forward_return > threshold`` else ``0``.
    * ``TERNARY`` — ``+1`` / ``0`` / ``-1`` with ``|forward_return| <= neutral_band``
      as the neutral class. ``neutral_band`` is non-negative.
    """

    kind: LabelKind
    horizon: Timeframe
    threshold: float | None = None
    neutral_band: float | None = None

    def __post_init__(self) -> None:
        if self.horizon.is_event_level:
            msg = "label horizon must be a bar duration, not tick"
            raise PredictiveSpecError(msg)
        if self.kind is LabelKind.REGRESSION:
            if self.threshold is not None or self.neutral_band is not None:
                msg = "REGRESSION label must not declare threshold or neutral_band"
                raise PredictiveSpecError(msg)
            return
        if self.kind is LabelKind.BINARY:
            if self.neutral_band is not None:
                msg = "BINARY label must not declare neutral_band"
                raise PredictiveSpecError(msg)
            if self.threshold is None:
                msg = "BINARY label requires threshold"
                raise PredictiveSpecError(msg)
            _require_finite_float(self.threshold, field_name="threshold")
            return
        if self.kind is LabelKind.TERNARY:
            if self.threshold is not None:
                msg = "TERNARY label must not declare threshold"
                raise PredictiveSpecError(msg)
            if self.neutral_band is None:
                msg = "TERNARY label requires neutral_band"
                raise PredictiveSpecError(msg)
            band = _require_finite_float(self.neutral_band, field_name="neutral_band")
            if band < 0.0:
                msg = "TERNARY neutral_band must be >= 0"
                raise PredictiveSpecError(msg)
            return
        assert_never(self.kind)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "kind": self.kind.value,
            "horizon": self.horizon.value,
        }
        if self.threshold is not None:
            payload["threshold"] = self.threshold
        if self.neutral_band is not None:
            payload["neutral_band"] = self.neutral_band
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> LabelSpec:
        try:
            kind = LabelKind(str(payload["kind"]))
            horizon = Timeframe(str(payload["horizon"]))
        except KeyError as exc:
            msg = f"label spec missing field: {exc.args[0]}"
            raise PredictiveSpecError(msg) from exc
        except ValueError as exc:
            msg = f"invalid label kind: {payload.get('kind')!r}"
            raise PredictiveSpecError(msg) from exc
        except ValidationError as exc:
            raise PredictiveSpecError(str(exc)) from exc

        threshold = _optional_finite_float(payload.get("threshold"), field_name="threshold")
        neutral_band = _optional_finite_float(
            payload.get("neutral_band"), field_name="neutral_band"
        )
        return cls(
            kind=kind,
            horizon=horizon,
            threshold=threshold,
            neutral_band=neutral_band,
        )


def _optional_finite_float(value: object, *, field_name: str) -> float | None:
    if value is None:
        return None
    return _require_finite_float(value, field_name=field_name)


def _require_finite_float(value: object, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        msg = f"{field_name} must be a finite number"
        raise PredictiveSpecError(msg)
    number = float(value)
    if not math.isfinite(number):
        msg = f"{field_name} must be a finite number"
        raise PredictiveSpecError(msg)
    return number
