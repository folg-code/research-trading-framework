"""Parameter schema, validation, and canonicalization."""

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from trading_framework.core.exceptions import ValidationError


class ParameterType(StrEnum):
    """Supported component parameter types."""

    INT = "int"
    FLOAT = "float"
    STR = "str"
    BOOL = "bool"


@dataclass(frozen=True, slots=True)
class ParameterFieldSpec:
    """Declaration of one typed component parameter."""

    name: str
    type: ParameterType
    default: int | float | str | bool | None = None
    minimum: float | None = None

    def __post_init__(self) -> None:
        normalized = self.name.strip()
        if not normalized:
            msg = "parameter name must be non-empty"
            raise ValidationError(msg)
        if normalized != self.name:
            object.__setattr__(self, "name", normalized)


@dataclass(frozen=True, slots=True)
class ParameterSchema:
    """Typed and validated parameter schema for one component."""

    fields: tuple[ParameterFieldSpec, ...]

    def __post_init__(self) -> None:
        names = [field.name for field in self.fields]
        if len(names) != len(set(names)):
            msg = "parameter schema contains duplicate field names"
            raise ValidationError(msg)

    def canonicalize(self, raw: Mapping[str, Any]) -> "CanonicalParameters":
        """Validate raw input, apply defaults, and return canonical parameters."""
        unknown = set(raw) - {field.name for field in self.fields}
        if unknown:
            msg = f"unknown parameters: {sorted(unknown)!r}"
            raise ValidationError(msg)

        canonical: dict[str, Any] = {}
        for field in self.fields:
            if field.name in raw:
                value = _coerce(field, raw[field.name])
            elif field.default is not None:
                value = field.default
            else:
                msg = f"missing required parameter: {field.name!r}"
                raise ValidationError(msg)
            canonical[field.name] = value
        return CanonicalParameters.from_mapping(canonical)


@dataclass(frozen=True, slots=True)
class CanonicalParameters:
    """Immutable canonical parameter values for fingerprinting."""

    _items: tuple[tuple[str, Any], ...]

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "CanonicalParameters":
        return cls(tuple(sorted(values.items(), key=lambda item: item[0])))

    def to_json_dict(self) -> dict[str, Any]:
        return dict(self._items)

    def get(self, name: str) -> Any:
        for key, value in self._items:
            if key == name:
                return value
        msg = f"parameter not found: {name!r}"
        raise ValidationError(msg)

    def fingerprint(self) -> str:
        return json.dumps(self.to_json_dict(), sort_keys=True, separators=(",", ":"))

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        return iter(self._items)


def _coerce(field: ParameterFieldSpec, value: Any) -> int | float | str | bool:
    if field.type is ParameterType.INT:
        if isinstance(value, bool) or not isinstance(value, int):
            msg = f"parameter {field.name!r} must be int"
            raise ValidationError(msg)
        coerced: int | float | str | bool = value
    elif field.type is ParameterType.FLOAT:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            msg = f"parameter {field.name!r} must be float"
            raise ValidationError(msg)
        coerced = float(value)
    elif field.type is ParameterType.STR:
        if not isinstance(value, str):
            msg = f"parameter {field.name!r} must be str"
            raise ValidationError(msg)
        coerced = value.strip()
        if not coerced:
            msg = f"parameter {field.name!r} must be non-empty"
            raise ValidationError(msg)
    elif field.type is ParameterType.BOOL:
        if not isinstance(value, bool):
            msg = f"parameter {field.name!r} must be bool"
            raise ValidationError(msg)
        coerced = value
    else:
        raise AssertionError(f"unsupported parameter type: {field.type!r}")

    if field.minimum is not None and isinstance(coerced, (int, float)) and coerced < field.minimum:
        msg = f"parameter {field.name!r} must be >= {field.minimum}"
        raise ValidationError(msg)
    return coerced
