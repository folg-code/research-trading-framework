"""Output identity and schema contracts."""

import re
from dataclasses import dataclass
from enum import StrEnum

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.alignment import AlignmentPolicy
from trading_framework.market_analysis.models.parameters import CanonicalParameters

_OUTPUT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class OutputId:
    """Stable semantic output identifier within one component."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not _OUTPUT_ID_PATTERN.fullmatch(normalized):
            msg = f"invalid output id: {self.value!r}"
            raise ValidationError(msg)
        if normalized != self.value:
            object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


class OutputGroup(StrEnum):
    """Output grouping for planner inclusion policy."""

    CORE = "core"
    DIAGNOSTIC = "diagnostic"
    RESEARCH = "research"


@dataclass(frozen=True, slots=True)
class OutputFieldSpec:
    """Declared output field in a component schema."""

    output_id: OutputId
    dtype: str
    group: OutputGroup = OutputGroup.CORE
    alignment_policy: AlignmentPolicy = AlignmentPolicy.LAST_CLOSED_BAR
    inactive_event_fill: float | None = None

    def __post_init__(self) -> None:
        normalized_dtype = self.dtype.strip().lower()
        if not normalized_dtype:
            msg = "output dtype must be non-empty"
            raise ValidationError(msg)
        if normalized_dtype != self.dtype:
            object.__setattr__(self, "dtype", normalized_dtype)
        if self.alignment_policy is AlignmentPolicy.EVENT_AT_AVAILABLE:
            if self.inactive_event_fill is None:
                msg = (
                    f"output {self.output_id.value!r} with EVENT_AT_AVAILABLE "
                    "must declare inactive_event_fill"
                )
                raise ValidationError(msg)
        elif self.inactive_event_fill is not None:
            msg = "inactive_event_fill is only valid for EVENT_AT_AVAILABLE outputs"
            raise ValidationError(msg)


@dataclass(frozen=True, slots=True)
class OutputSchema:
    """Declared outputs for one component."""

    outputs: tuple[OutputFieldSpec, ...]

    def __post_init__(self) -> None:
        names = [field.output_id.value for field in self.outputs]
        if len(names) != len(set(names)):
            msg = "output schema contains duplicate output ids"
            raise ValidationError(msg)

    def core_output_ids(self) -> tuple[OutputId, ...]:
        return tuple(field.output_id for field in self.outputs if field.group is OutputGroup.CORE)


@dataclass(frozen=True, slots=True)
class ComponentOutputRef:
    """Reference to a specific output of another component request."""

    component_id: ComponentId
    parameters: CanonicalParameters
    output_id: OutputId

    def canonical_key(self) -> str:
        return f"{self.component_id}:{self.parameters.fingerprint()}:{self.output_id}"
