"""Base identifier value object."""

from dataclasses import dataclass

from trading_framework.core.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class Identifier:
    """Immutable, validated string identifier."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            msg = "identifier value must be non-empty"
            raise ValidationError(msg)
        if normalized != self.value:
            object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
