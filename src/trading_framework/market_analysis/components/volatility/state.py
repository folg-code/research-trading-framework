"""Volatility state component with diagnostic output."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    dependency_results_values,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.components.volatility.atr import AtrComponent
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
    ComponentOutputRef,
    OutputFieldSpec,
    OutputGroup,
    OutputId,
    OutputSchema,
)
from trading_framework.market_analysis.models.parameters import (
    CanonicalParameters,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
)
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("volatility.state")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.volatility_state")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")
_ATR_ID = ComponentId("volatility.atr")
_STATE_OUTPUT = OutputId("state")
_DISTANCE_OUTPUT = OutputId("distance_to_threshold")
_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("period", ParameterType.INT, default=14, minimum=1),
        ParameterFieldSpec("threshold", ParameterType.FLOAT, default=5.0, minimum=0.0),
    )
)
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_STATE_OUTPUT, "float64", group=OutputGroup.CORE),
        OutputFieldSpec(_DISTANCE_OUTPUT, "float64", group=OutputGroup.DIAGNOSTIC),
    )
)


class VolatilityStateComponent:
    """High-volatility state derived from ATR and a threshold."""

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.STATE
    causality = Causality.CAUSAL
    parameter_schema = _PARAMETER_SCHEMA
    output_schema = _OUTPUT_SCHEMA

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        return HistoryRequirement(bars_before=int(parameters.get("period")))

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        period = int(parameters.get("period"))
        atr_parameters = AtrComponent().parameter_schema.canonicalize({"period": period})
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_ATR_ID,
                    parameters=atr_parameters,
                    output_id=OutputId("value"),
                )
            ),
        )

    def data_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[DataFieldDependency, ...]:
        return ()


class NumpyVolatilityStateImplementation:
    """NumPy volatility state backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        period = int(parameters.get("period"))
        threshold = float(parameters.get("threshold"))
        bar_count = len(workspace.market)
        atr_values = dependency_results_values(
            workspace.dependency_results,
            output_id=OutputId("value"),
        )
        distance = atr_values - threshold
        state = np.where(np.isnan(atr_values), np.nan, np.where(atr_values >= threshold, 1.0, 0.0))
        warmup_bars = period - 1
        dependency_keys = tuple(sorted(workspace.dependency_results))
        return build_analysis_result(
            context=context,
            component_id=_COMPONENT_ID,
            component_version=_COMPONENT_VERSION,
            implementation_id=_IMPLEMENTATION_ID,
            implementation_version=_IMPLEMENTATION_VERSION,
            parameters=parameters,
            dependency_keys=dependency_keys,
            output_schema=_OUTPUT_SCHEMA,
            outputs={
                _STATE_OUTPUT: ndarray_to_output_series(state),
                _DISTANCE_OUTPUT: ndarray_to_output_series(distance),
            },
            warmup_bars=warmup_bars,
            valid_from_index=warmup_bars,
            bar_count=bar_count,
        )


__all__ = ["NumpyVolatilityStateImplementation", "VolatilityStateComponent"]
