"""Component request contract."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.parameters import CanonicalParameters, ParameterSchema


@dataclass(frozen=True, slots=True)
class ComponentRequest:
    """User or planner intent to compute one semantic component."""

    component_id: ComponentId
    parameters: CanonicalParameters

    @classmethod
    def from_raw(
        cls,
        component_id: ComponentId,
        schema: ParameterSchema,
        raw: Mapping[str, Any],
    ) -> "ComponentRequest":
        return cls(component_id=component_id, parameters=schema.canonicalize(raw))
