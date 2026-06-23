"""Market Analysis identity model tests."""

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis import (
    ComponentId,
    ComponentVersion,
    ImplementationId,
)


def test_component_id_accepts_dotted_semantic_name() -> None:
    component_id = ComponentId("volatility.atr")
    assert str(component_id) == "volatility.atr"


@pytest.mark.parametrize(
    "value",
    ["ATR", "volatility", "volatility.", ".atr", "volatility..atr"],
)
def test_component_id_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValidationError):
        ComponentId(value)


def test_implementation_id_is_distinct_type_from_component_id() -> None:
    component = ComponentId("volatility.atr")
    implementation = ImplementationId("numpy.atr")
    assert str(component) != str(implementation)


def test_versions_require_semver() -> None:
    assert ComponentVersion("1.0.0").value == "1.0.0"
    with pytest.raises(ValidationError):
        ComponentVersion("1.0")
