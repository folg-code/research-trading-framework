"""Resolved computation identity."""

import json
from dataclasses import dataclass

from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.identity.component import (
    ComponentId,
    ComponentVersion,
    ImplementationId,
    ImplementationVersion,
)
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.time.models.timeframe import Timeframe


@dataclass(frozen=True, slots=True)
class ComputationIdentity:
    """Fully resolved identity of one component computation (computation-stage cache key)."""

    component_id: ComponentId
    component_version: ComponentVersion
    implementation_id: ImplementationId
    implementation_version: ImplementationVersion
    parameters: CanonicalParameters
    dataset_ref: DatasetRef
    computation_timeframe: Timeframe
    requested_range: TimeRange
    dependency_keys: tuple[str, ...]
    input_identity_key: str | None = None

    @property
    def timeframe(self) -> Timeframe:
        """Backward-compatible alias for ``computation_timeframe``."""
        return self.computation_timeframe

    def canonical_key(self) -> str:
        """Return a stable string key suitable for computation-stage cache lookup."""
        payload = {
            "kind": "component_computation",
            "component_id": str(self.component_id),
            "component_version": str(self.component_version),
            "implementation_id": str(self.implementation_id),
            "implementation_version": str(self.implementation_version),
            "parameters": self.parameters.to_json_dict(),
            "dataset_ref": str(self.dataset_ref),
            "computation_timeframe": self.computation_timeframe.value,
            "requested_range": self.requested_range.canonical(),
            "dependency_keys": list(self.dependency_keys),
            "input_identity_key": self.input_identity_key,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def __hash__(self) -> int:
        return hash(self.canonical_key())
