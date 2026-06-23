"""Parameter schema and canonicalization tests."""

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis import (
    CanonicalParameters,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
)


def _atr_schema() -> ParameterSchema:
    return ParameterSchema(
        fields=(ParameterFieldSpec("period", ParameterType.INT, default=14, minimum=1.0),)
    )


def test_canonicalize_applies_defaults() -> None:
    params = _atr_schema().canonicalize({})
    assert params.get("period") == 14


def test_canonicalize_is_deterministic_for_fingerprint() -> None:
    schema = ParameterSchema(
        fields=(
            ParameterFieldSpec("period", ParameterType.INT, default=14),
            ParameterFieldSpec("threshold", ParameterType.FLOAT, default=1.5),
        )
    )
    first = schema.canonicalize({"threshold": 2.0})
    second = schema.canonicalize({"period": 14, "threshold": 2.0})
    assert first.fingerprint() == second.fingerprint()


def test_unknown_parameters_are_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown parameters"):
        _atr_schema().canonicalize({"period": 14, "foo": 1})


def test_canonical_parameters_json_dict_is_sorted() -> None:
    params = CanonicalParameters.from_mapping({"b": 2, "a": 1})
    assert params.to_json_dict() == {"a": 1, "b": 2}
