"""Structure Fibonacci Extension Level Market Analysis component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.fibonacci_level import fibonacci_level
from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.components.structure.swing import SwingStructureComponent
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
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("structure.fibonacci_extension_level")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.fibonacci_extension_level")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_SWING_ID = ComponentId("structure.swing")
_LATEST_SWING_HIGH_LEVEL = OutputId("latest_swing_high_level")
_LATEST_SWING_LOW_LEVEL = OutputId("latest_swing_low_level")
_LATEST_SWING_HIGH_OBSERVED_INDEX = OutputId("latest_swing_high_observed_index")
_LATEST_SWING_LOW_OBSERVED_INDEX = OutputId("latest_swing_low_observed_index")
_VALUE = OutputId("value")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("pivot_range", ParameterType.INT, default=2, minimum=1),
        ParameterFieldSpec("ratio", ParameterType.FLOAT, default=1.618, minimum=0.0),
    )
)
_OUTPUT_SCHEMA = OutputSchema(outputs=(OutputFieldSpec(_VALUE, "float64"),))


class FibonacciExtensionLevelComponent:
    """Causal Fibonacci extension level of the most recent confirmed swing leg (IDEA-032).

    Same "active leg" definition as ``structure.fibonacci_retracement_level``
    (an up-leg or down-leg between ``structure.swing``'s latest confirmed
    swing high/low, chosen by whichever extreme was confirmed most
    recently), but projecting BEYOND the leg's own most recent extreme in
    its original direction, rather than pulling back into it:

        range = latest_swing_high_level - latest_swing_low_level
        value[up-leg]   = low  + ratio * range   -- projects beyond the high
        value[down-leg] = high - ratio * range   -- projects beyond the low

    ``ratio`` defaults to the standard `1.618` extension level; `ratio >
    1.0` projects past the leg's own most recent extreme (the conventional
    usage), though this component does not enforce that minimum -- a
    `ratio <= 1.0` value is still a well-defined point along the same
    line, just inside the leg's own range. No zero-denominator case: a
    linear extrapolation along ``range``, never a division. ``NaN`` until
    both a swing high and a swing low have been confirmed at least once.

    Depends on ``structure.swing`` (keyed by ``pivot_range``). Warm-up:
    the dependency's own ``valid_from_index``.
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
        pivot_range = int(parameters.get("pivot_range"))
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_SWING_ID,
                    parameters=SwingStructureComponent().parameter_schema.canonicalize(
                        {"pivot_range": pivot_range}
                    ),
                    output_id=_LATEST_SWING_HIGH_LEVEL,
                )
            ),
        )


class NumpyFibonacciExtensionLevelImplementation:
    """NumPy Fibonacci Extension Level backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        ratio = float(parameters.get("ratio"))
        bar_count = len(workspace.market)

        swing_result = next(iter(workspace.dependency_results.values()))
        latest_swing_high_level = np.asarray(
            swing_result.outputs[_LATEST_SWING_HIGH_LEVEL].values, dtype=np.float64
        )
        latest_swing_low_level = np.asarray(
            swing_result.outputs[_LATEST_SWING_LOW_LEVEL].values, dtype=np.float64
        )
        latest_swing_high_observed_index = np.asarray(
            swing_result.outputs[_LATEST_SWING_HIGH_OBSERVED_INDEX].values, dtype=np.float64
        )
        latest_swing_low_observed_index = np.asarray(
            swing_result.outputs[_LATEST_SWING_LOW_OBSERVED_INDEX].values, dtype=np.float64
        )

        value = fibonacci_level(
            latest_swing_high_level,
            latest_swing_low_level,
            latest_swing_high_observed_index,
            latest_swing_low_observed_index,
            ratio=ratio,
            is_extension=True,
        )

        warmup_bars = swing_result.validity.valid_from_index
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
            outputs={_VALUE: ndarray_to_output_series(value)},
            warmup_bars=warmup_bars,
            valid_from_index=warmup_bars,
            bar_count=bar_count,
            workspace=workspace,
        )


__all__ = [
    "FibonacciExtensionLevelComponent",
    "NumpyFibonacciExtensionLevelImplementation",
]
