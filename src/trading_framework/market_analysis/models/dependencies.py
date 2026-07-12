"""Component dependency declarations."""

from dataclasses import dataclass

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.models.outputs import ComponentOutputRef

_ALLOWED_DATA_FIELDS = frozenset({"open", "high", "low", "close", "volume"})


@dataclass(frozen=True, slots=True)
class DataFieldDependency:
    """Declared dependency on one canonical market-data column."""

    field: str

    def __post_init__(self) -> None:
        normalized = self.field.strip().lower()
        if normalized not in _ALLOWED_DATA_FIELDS:
            msg = f"unsupported data field dependency: {self.field!r}"
            raise ValidationError(msg)
        if normalized != self.field:
            object.__setattr__(self, "field", normalized)


@dataclass(frozen=True, slots=True)
class ComponentDependency:
    """Declared dependency on a specific output of another component."""

    output_ref: ComponentOutputRef

    def canonical_key(self) -> str:
        return self.output_ref.canonical_key()
