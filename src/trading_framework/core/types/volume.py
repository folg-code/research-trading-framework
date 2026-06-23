"""Volume value object for market facts."""

from dataclasses import dataclass

from trading_framework.core.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class Volume:
    """Immutable non-negative traded volume."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            msg = "volume must be non-negative"
            raise ValidationError(msg)

    def __str__(self) -> str:
        return str(self.value)

    def to_json(self) -> int:
        """Return the canonical JSON representation."""
        return self.value

    @classmethod
    def from_json(cls, value: int) -> "Volume":
        """Parse a volume from its canonical JSON integer form."""
        return cls(value)
