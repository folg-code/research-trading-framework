"""Component and implementation identity types."""

import re
from dataclasses import dataclass

from trading_framework.core.exceptions import ValidationError

_COMPONENT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
_IMPLEMENTATION_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def _validate_dotted_id(value: str, pattern: re.Pattern[str], label: str) -> str:
    normalized = value.strip()
    if not normalized:
        msg = f"{label} must be non-empty"
        raise ValidationError(msg)
    if not pattern.fullmatch(normalized):
        msg = f"invalid {label}: {value!r}"
        raise ValidationError(msg)
    return normalized


@dataclass(frozen=True, slots=True)
class ComponentId:
    """Semantic component identifier, e.g. ``volatility.atr``."""

    value: str

    def __post_init__(self) -> None:
        normalized = _validate_dotted_id(self.value, _COMPONENT_ID_PATTERN, "component id")
        if normalized != self.value:
            object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ImplementationId:
    """Backend implementation identifier, e.g. ``numpy.atr``."""

    value: str

    def __post_init__(self) -> None:
        normalized = _validate_dotted_id(
            self.value,
            _IMPLEMENTATION_ID_PATTERN,
            "implementation id",
        )
        if normalized != self.value:
            object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ComponentVersion:
    """Semantic version of a component contract."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not _VERSION_PATTERN.fullmatch(normalized):
            msg = f"invalid component version: {self.value!r}"
            raise ValidationError(msg)
        if normalized != self.value:
            object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ImplementationVersion:
    """Semantic version of a component implementation."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not _VERSION_PATTERN.fullmatch(normalized):
            msg = f"invalid implementation version: {self.value!r}"
            raise ValidationError(msg)
        if normalized != self.value:
            object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
