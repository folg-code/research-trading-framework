"""Analysis result contract."""

from collections.abc import Mapping
from dataclasses import dataclass

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.identity.computation import ComputationIdentity
from trading_framework.market_analysis.models.availability import AvailabilityMetadata
from trading_framework.market_analysis.models.history import WarmUpMetadata
from trading_framework.market_analysis.models.lineage import Lineage
from trading_framework.market_analysis.models.outputs import OutputId, OutputSchema


@dataclass(frozen=True, slots=True)
class OutputSeries:
    """Immutable output payload contract without backend-specific array types."""

    values: tuple[float, ...]
    dtype: str = "float64"

    def __post_init__(self) -> None:
        normalized_dtype = self.dtype.strip().lower()
        if not normalized_dtype:
            msg = "dtype must be non-empty"
            raise ValidationError(msg)
        if normalized_dtype != self.dtype:
            object.__setattr__(self, "dtype", normalized_dtype)

    @property
    def length(self) -> int:
        return len(self.values)


@dataclass(frozen=True, slots=True)
class ValidityMetadata:
    """Returned valid range and missing-value semantics for one result."""

    valid_from_index: int
    valid_to_index: int
    missing_value_semantics: str = "nan"

    def __post_init__(self) -> None:
        if self.valid_from_index < 0:
            msg = "valid_from_index must be >= 0"
            raise ValidationError(msg)
        if self.valid_to_index < self.valid_from_index:
            msg = "valid_to_index must be >= valid_from_index"
            raise ValidationError(msg)


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Standardized result of one resolved computation."""

    computation_identity: ComputationIdentity
    output_schema: OutputSchema
    outputs: Mapping[OutputId, OutputSeries]
    lineage: Lineage
    validity: ValidityMetadata
    warmup: WarmUpMetadata
    availability: AvailabilityMetadata
    diagnostics: Mapping[str, str]

    def __post_init__(self) -> None:
        schema_ids = {field.output_id for field in self.output_schema.outputs}
        output_ids = set(self.outputs)
        if output_ids != schema_ids:
            msg = "outputs must match declared output schema"
            raise ValidationError(msg)
