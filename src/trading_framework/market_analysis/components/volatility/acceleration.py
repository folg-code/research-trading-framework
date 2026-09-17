"""Volatility Acceleration Market Analysis component."""

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
    OutputId,
    OutputSchema,
)
from trading_framework.market_analysis.models.parameters import (
    CanonicalParameters,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
)
from trading_framework.market_analysis.models.result import AnalysisResult, OutputSeries
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("volatility.acceleration")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.acceleration")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_ATR_ID = ComponentId("volatility.atr")
_ATR_VALUE_OUTPUT = OutputId("value")
_VALUE = OutputId("value")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(ParameterFieldSpec("period", ParameterType.INT, default=14, minimum=1),)
)
_OUTPUT_SCHEMA = OutputSchema(outputs=(OutputFieldSpec(_VALUE, "float64"),))


class AccelerationComponent:
    """Causal first difference of ATR: the rate of change of volatility itself.

    ``value = atr[i] - atr[i-1]`` -- not a rate of change of price. Depends
    on ``volatility.atr`` keyed by ``period``. Warm-up: ``period`` bars
    (ATR's own ``period - 1`` warmup, plus one more bar so both ``atr[i]``
    and ``atr[i-1]`` are valid). No zero-denominator case: a plain
    difference, never a division.
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
        return ()

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        period = int(parameters.get("period"))
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_ATR_ID,
                    parameters=AtrComponent().parameter_schema.canonicalize({"period": period}),
                    output_id=_ATR_VALUE_OUTPUT,
                )
            ),
        )


class NumpyAccelerationImplementation:
    """NumPy Acceleration backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        period = int(parameters.get("period"))
        bar_count = len(workspace.market)

        atr_values = dependency_results_values(
            workspace.dependency_results,
            output_id=_ATR_VALUE_OUTPUT,
        )
        prev_atr = np.roll(atr_values, 1)
        prev_atr[0] = np.nan
        value = atr_values - prev_atr

        outputs: dict[OutputId, OutputSeries] = {_VALUE: ndarray_to_output_series(value)}
        warmup_bars = period
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
            outputs=outputs,
            warmup_bars=warmup_bars,
            valid_from_index=warmup_bars,
            bar_count=bar_count,
            workspace=workspace,
        )


__all__ = ["AccelerationComponent", "NumpyAccelerationImplementation"]
