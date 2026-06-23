"""Component request tests."""

from trading_framework.market_analysis import (
    ComponentId,
    ComponentRequest,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
)


def test_component_request_from_raw_validates_and_canonicalizes() -> None:
    schema = ParameterSchema(fields=(ParameterFieldSpec("period", ParameterType.INT, default=14),))
    request = ComponentRequest.from_raw(
        ComponentId("volatility.atr"),
        schema,
        {"period": 21},
    )
    assert request.component_id.value == "volatility.atr"
    assert request.parameters.get("period") == 21
