"""Adapter contract suite for NumPy implementations (D-033)."""

import pytest

from trading_framework.market_analysis.components.structure import (
    NumpySessionRangeImplementation,
    SessionRangeComponent,
)
from trading_framework.market_analysis.components.trend import (
    EmaComponent,
    NumpyEmaImplementation,
    NumpySlopeImplementation,
    SlopeComponent,
)
from trading_framework.market_analysis.components.volatility import (
    AtrComponent,
    NumpyAtrImplementation,
    NumpyTrueRangeImplementation,
    TrueRangeComponent,
)

from .adapter_contract import (
    AdapterContractCase,
    assert_adapter_contract,
    dependency_workspace,
    session_metadata_workspace,
)


@pytest.mark.parametrize(
    "case",
    [
        AdapterContractCase(
            component=TrueRangeComponent(),
            implementation=NumpyTrueRangeImplementation(),
            parameters=TrueRangeComponent().parameter_schema.canonicalize({}),
            dependency_keys=(),
        ),
        AdapterContractCase(
            component=AtrComponent(),
            implementation=NumpyAtrImplementation(),
            parameters=AtrComponent().parameter_schema.canonicalize({"period": 3}),
            dependency_keys=(),
            prepare_workspace=dependency_workspace(
                component_id=TrueRangeComponent().component_id,
                parameters=TrueRangeComponent().parameter_schema.canonicalize({}),
            ),
        ),
        AdapterContractCase(
            component=EmaComponent(),
            implementation=NumpyEmaImplementation(),
            parameters=EmaComponent().parameter_schema.canonicalize({"period": 3}),
            dependency_keys=(),
        ),
        AdapterContractCase(
            component=SlopeComponent(),
            implementation=NumpySlopeImplementation(),
            parameters=SlopeComponent().parameter_schema.canonicalize({"period": 3}),
            dependency_keys=(),
        ),
        AdapterContractCase(
            component=SessionRangeComponent(),
            implementation=NumpySessionRangeImplementation(),
            parameters=SessionRangeComponent().parameter_schema.canonicalize({}),
            dependency_keys=(),
            prepare_workspace=session_metadata_workspace(),
        ),
    ],
    ids=["true_range", "atr", "ema", "slope", "session_range"],
)
def test_numpy_adapter_satisfies_shared_contract(case: AdapterContractCase) -> None:
    assert_adapter_contract(case)
