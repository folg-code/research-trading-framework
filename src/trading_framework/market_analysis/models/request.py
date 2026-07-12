"""Component request contract."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.parameters import CanonicalParameters, ParameterSchema
from trading_framework.market_analysis.models.timeframes import validate_computation_timeframe
from trading_framework.time.models.timeframe import Timeframe


@dataclass(frozen=True, slots=True)
class ComponentRequest:
    """User or planner intent to compute one semantic component."""

    component_id: ComponentId
    parameters: CanonicalParameters
    computation_timeframe: Timeframe | None = None

    def __post_init__(self) -> None:
        if self.computation_timeframe is None:
            return
        normalized = Timeframe(self.computation_timeframe.value)
        if normalized != self.computation_timeframe:
            object.__setattr__(self, "computation_timeframe", normalized)

    @classmethod
    def from_raw(
        cls,
        component_id: ComponentId,
        schema: ParameterSchema,
        raw: Mapping[str, Any],
        *,
        computation_timeframe: Timeframe | None = None,
    ) -> "ComponentRequest":
        return cls(
            component_id=component_id,
            parameters=schema.canonicalize(raw),
            computation_timeframe=computation_timeframe,
        )

    def resolved_computation_timeframe(self, *, source_timeframe: Timeframe) -> Timeframe:
        """Return computation timeframe after applying source dataset default."""
        if self.computation_timeframe is None:
            return source_timeframe
        validate_computation_timeframe(
            source_timeframe=source_timeframe,
            computation_timeframe=self.computation_timeframe,
        )
        return self.computation_timeframe
