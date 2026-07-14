"""Configuration for deriving OHLCV from published continuous trades."""

from __future__ import annotations

from dataclasses import dataclass

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.market.continuous.identity import CONTINUOUS_TRADES_PROVIDER
from trading_framework.market.continuous.policy import VOLUME_RTH_CLOSE_POLICY_SLUG
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.derivation.config import (
    DERIVED_OHLCV_PROVIDER,
    TRADES_TO_BARS_DERIVATION_METHOD,
    TRADES_TO_BARS_VERSION,
)
from trading_framework.time.models.timeframe import Timeframe

_SUPPORTED_TARGET_TIMEFRAME = Timeframe("1m")


def roll_schedule_ref(*, product: str, policy_slug: str, version: int) -> str:
    """Return the canonical storage reference for one roll schedule version."""
    return f"continuous/schedules/{product}/{policy_slug}/v{version}"


@dataclass(frozen=True, slots=True)
class DerivedContinuousOhlcvConfig:
    """Settings for deriving OHLCV bars from published continuous trades."""

    source_continuous_trades_ref: DatasetRef
    target_dataset_id: DatasetId
    schema_version: str
    normalization_version: str = TRADES_TO_BARS_VERSION
    target_timeframe: Timeframe = _SUPPORTED_TARGET_TIMEFRAME

    def __post_init__(self) -> None:
        source = self.source_continuous_trades_ref.dataset_id
        if source.data_type != "trades":
            msg = f"source dataset data_type must be trades, got {source.data_type!r}"
            raise ValidationError(msg)
        if source.provider != CONTINUOUS_TRADES_PROVIDER:
            msg = f"source dataset provider must be {CONTINUOUS_TRADES_PROVIDER!r}"
            raise ValidationError(msg)
        if not source.timeframe.is_event_level:
            msg = "source dataset timeframe must be tick"
            raise ValidationError(msg)

        target = self.target_dataset_id
        if target.data_type != "ohlcv":
            msg = f"target dataset data_type must be ohlcv, got {target.data_type!r}"
            raise ValidationError(msg)
        if target.provider != DERIVED_OHLCV_PROVIDER:
            msg = f"target dataset provider must be {DERIVED_OHLCV_PROVIDER!r}"
            raise ValidationError(msg)
        if self.target_timeframe != _SUPPORTED_TARGET_TIMEFRAME:
            msg = f"Sprint 015 MVP supports target timeframe 1m only, got {self.target_timeframe!r}"
            raise ValidationError(msg)
        if target.timeframe != self.target_timeframe:
            msg = "target_dataset_id.timeframe must match target_timeframe"
            raise ValidationError(msg)
        if source.instrument_id != target.instrument_id:
            msg = "source and target dataset instrument_id must match"
            raise ValidationError(msg)
        if target.source_id != VOLUME_RTH_CLOSE_POLICY_SLUG:
            msg = f"target source_id must be {VOLUME_RTH_CLOSE_POLICY_SLUG!r}"
            raise ValidationError(msg)

        if not self.schema_version.strip():
            msg = "schema_version must be non-empty"
            raise ValidationError(msg)
        if not self.normalization_version.strip():
            msg = "normalization_version must be non-empty"
            raise ValidationError(msg)

    def lineage(
        self,
        *,
        product: str,
        policy_slug: str,
        roll_schedule_version: int,
    ) -> dict[str, str]:
        """Return required lineage metadata for the derived continuous OHLCV dataset."""
        return {
            "continuous_trades_dataset_ref": str(self.source_continuous_trades_ref),
            "roll_schedule_ref": roll_schedule_ref(
                product=product,
                policy_slug=policy_slug,
                version=roll_schedule_version,
            ),
            "roll_schedule_version": str(roll_schedule_version),
            "derivation_method": TRADES_TO_BARS_DERIVATION_METHOD,
            "derivation_version": self.normalization_version,
            "target_timeframe": self.target_timeframe.value,
        }

    @property
    def instrument_id(self) -> Identifier:
        """Return the instrument identity shared by source and target datasets."""
        return self.target_dataset_id.instrument_id
