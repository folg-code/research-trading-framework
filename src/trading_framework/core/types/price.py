"""Price value object for OHLC market fields."""

from dataclasses import dataclass
from decimal import Decimal

from trading_framework.core.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class Price:
    """Immutable decimal price."""

    value: Decimal

    def __post_init__(self) -> None:
        decimal_value = self.value if isinstance(self.value, Decimal) else Decimal(str(self.value))
        if decimal_value != self.value:
            object.__setattr__(self, "value", decimal_value)
        if not self.value.is_finite():
            msg = "price must be a finite decimal"
            raise ValidationError(msg)

    def __str__(self) -> str:
        return format(self.value, "f")

    def to_json(self) -> str:
        """Return the canonical JSON representation."""
        return str(self.value)

    @classmethod
    def from_json(cls, value: str) -> "Price":
        """Parse a price from its canonical JSON string form."""
        return cls(Decimal(value))
