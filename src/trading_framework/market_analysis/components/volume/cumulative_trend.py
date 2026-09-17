"""Volume Cumulative Trend Market Analysis component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.cumulative_trend import cumulative_trend
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
from trading_framework.market_analysis.models.outputs import (
    OutputFieldSpec,
    OutputId,
    OutputSchema,
)
from trading_framework.market_analysis.models.parameters import CanonicalParameters, ParameterSchema
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("volume.cumulative_trend")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.cumulative_trend")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")
_VALUE = OutputId("value")
_PARAMETER_SCHEMA = ParameterSchema(fields=())
_OUTPUT_SCHEMA = OutputSchema(outputs=(OutputFieldSpec(_VALUE, "float64"),))


class CumulativeTrendComponent:
    """Causal cumulative volume signed by price direction (formerly "Price Volume Trend").

    ``value[0] = 0.0``; ``value[i] = value[i-1] + volume[i] * (close[i] -
    close[i-1]) / close[i-1]`` for ``i >= 1`` -- volume added on up bars,
    subtracted on down bars, scaled by the bar's own percent price change
    (not a flat sign, unlike its simpler cousin On-Balance Volume). No
    external period parameter, so no warm-up: every bar is valid
    immediately.
    """

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = _PARAMETER_SCHEMA
    output_schema = _OUTPUT_SCHEMA

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        return HistoryRequirement(bars_before=0)

    def data_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[DataFieldDependency, ...]:
        return (
            DataFieldDependency("close"),
            DataFieldDependency("volume"),
        )

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        return ()


class NumpyCumulativeTrendImplementation:
    """NumPy Cumulative Trend backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        bar_count = len(workspace.market)
        close = np.asarray(workspace.market.close.values, dtype=np.float64)
        volume = np.asarray(workspace.market.volume.values, dtype=np.float64)
        values = cumulative_trend(close, volume)
        return build_analysis_result(
            context=context,
            component_id=_COMPONENT_ID,
            component_version=_COMPONENT_VERSION,
            implementation_id=_IMPLEMENTATION_ID,
            implementation_version=_IMPLEMENTATION_VERSION,
            parameters=parameters,
            dependency_keys=(),
            output_schema=_OUTPUT_SCHEMA,
            outputs={_VALUE: ndarray_to_output_series(values)},
            warmup_bars=0,
            valid_from_index=0,
            bar_count=bar_count,
            workspace=workspace,
        )


__all__ = ["CumulativeTrendComponent", "NumpyCumulativeTrendImplementation"]
