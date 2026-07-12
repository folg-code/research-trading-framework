"""True Range feature component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.kernels import true_range
from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.identity.component import (
    ComponentId,
    ComponentVersion,
    ImplementationId,
    ImplementationVersion,
)
from trading_framework.market_analysis.models.context import AnalysisContext
from trading_framework.market_analysis.models.dependencies import (
    ComponentDependency,
    DataFieldDependency,
)
from trading_framework.market_analysis.models.history import HistoryRequirement
from trading_framework.market_analysis.models.kind import Causality, ComponentKind
from trading_framework.market_analysis.models.outputs import OutputFieldSpec, OutputId, OutputSchema
from trading_framework.market_analysis.models.parameters import CanonicalParameters, ParameterSchema
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("volatility.true_range")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.true_range")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")
_OUTPUT_ID = OutputId("value")
_OUTPUT_SCHEMA = OutputSchema(outputs=(OutputFieldSpec(_OUTPUT_ID, "float64"),))
_PARAMETER_SCHEMA = ParameterSchema(fields=())
_WARMUP_BARS = 1


class TrueRangeComponent:
    """Semantic true range feature over canonical OHLC columns."""

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = _PARAMETER_SCHEMA
    output_schema = _OUTPUT_SCHEMA

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        return HistoryRequirement(bars_before=_WARMUP_BARS)

    def data_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[DataFieldDependency, ...]:
        return (
            DataFieldDependency("high"),
            DataFieldDependency("low"),
            DataFieldDependency("close"),
        )

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        return ()


class NumpyTrueRangeImplementation:
    """NumPy true range backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        market = workspace.market
        bar_count = len(market)
        high = np.asarray(market.high.values, dtype=np.float64)
        low = np.asarray(market.low.values, dtype=np.float64)
        close = np.asarray(market.close.values, dtype=np.float64)
        values = true_range(high, low, close)
        return build_analysis_result(
            context=context,
            component_id=_COMPONENT_ID,
            component_version=_COMPONENT_VERSION,
            implementation_id=_IMPLEMENTATION_ID,
            implementation_version=_IMPLEMENTATION_VERSION,
            parameters=parameters,
            dependency_keys=(),
            output_schema=_OUTPUT_SCHEMA,
            outputs={_OUTPUT_ID: ndarray_to_output_series(values)},
            warmup_bars=_WARMUP_BARS,
            valid_from_index=_WARMUP_BARS,
            bar_count=bar_count,
            workspace=workspace,
        )


__all__ = ["NumpyTrueRangeImplementation", "TrueRangeComponent"]
