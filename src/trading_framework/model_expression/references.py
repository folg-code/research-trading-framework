"""Model-layer references to Market Analysis outputs and canonical market fields."""

from dataclasses import dataclass
from enum import StrEnum

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.assembly.assembler import default_alias
from trading_framework.market_analysis.assembly.frame import AnalysisFrameColumnSpec
from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.identity.computation import ComputationIdentity
from trading_framework.market_analysis.models.outputs import OutputId
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.market_analysis.models.request import ComponentRequest
from trading_framework.time.models.timeframe import Timeframe


class MarketField(StrEnum):
    """Canonical OHLCV fields on the evaluation grid."""

    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    VOLUME = "volume"


@dataclass(frozen=True, slots=True)
class MarketFieldReference:
    """Reference to one canonical market field on the evaluation timeframe."""

    field: MarketField

    def frame_column_key(self) -> str:
        return self.field.value

    def dependency_key(self) -> str:
        return f"market:{self.field.value}"


@dataclass(frozen=True, slots=True)
class ComponentOutputReference:
    """Reference to one aligned component output column on the evaluation grid."""

    component_id: ComponentId
    parameters: CanonicalParameters
    output_id: OutputId
    computation_timeframe: Timeframe | None = None
    alias: str | None = None

    def __post_init__(self) -> None:
        if self.alias is not None and not self.alias.strip():
            msg = "alias must be non-empty when provided"
            raise ValidationError(msg)

    def to_component_request(self) -> ComponentRequest:
        return ComponentRequest(
            component_id=self.component_id,
            parameters=self.parameters,
            computation_timeframe=self.computation_timeframe,
        )

    def to_frame_column_spec(self) -> AnalysisFrameColumnSpec:
        return AnalysisFrameColumnSpec(
            component_id=self.component_id,
            parameters=self.parameters,
            output_id=self.output_id,
            alias=self.alias,
        )

    def dependency_key(self) -> str:
        timeframe = (
            self.computation_timeframe.value if self.computation_timeframe is not None else "source"
        )
        return (
            f"component:{self.component_id}:{self.parameters.fingerprint()}:"
            f"{timeframe}:{self.output_id}"
        )

    def resolve_frame_column_key(self, *, computation_identity: ComputationIdentity) -> str:
        if self.alias is not None:
            return self.alias
        return default_alias(computation_identity, self.output_id)


__all__ = [
    "ComponentOutputReference",
    "MarketField",
    "MarketFieldReference",
]
