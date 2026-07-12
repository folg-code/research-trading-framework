"""Lineage metadata for analysis results."""

from dataclasses import dataclass
from datetime import datetime

from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.identity.component import (
    ComponentId,
    ComponentVersion,
    ImplementationId,
    ImplementationVersion,
)
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.time.models.utc_instant import require_utc_aware


@dataclass(frozen=True, slots=True)
class Lineage:
    """Mandatory provenance metadata for one analysis result."""

    dataset_ref: DatasetRef
    component_id: ComponentId
    component_version: ComponentVersion
    implementation_id: ImplementationId
    implementation_version: ImplementationVersion
    parameters: CanonicalParameters
    dependency_keys: tuple[str, ...]
    engine_version: str
    executed_at: datetime

    def __post_init__(self) -> None:
        executed_at = require_utc_aware(self.executed_at)
        if executed_at != self.executed_at:
            object.__setattr__(self, "executed_at", executed_at)

    def to_json_dict(self) -> dict[str, object]:
        return {
            "dataset_ref": str(self.dataset_ref),
            "component_id": str(self.component_id),
            "component_version": str(self.component_version),
            "implementation_id": str(self.implementation_id),
            "implementation_version": str(self.implementation_version),
            "parameters": self.parameters.to_json_dict(),
            "dependency_keys": list(self.dependency_keys),
            "engine_version": self.engine_version,
            "executed_at": self.executed_at.isoformat(),
        }
