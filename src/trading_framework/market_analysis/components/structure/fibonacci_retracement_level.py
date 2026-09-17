"""Structure Fibonacci Retracement Level Market Analysis component."""

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

_COMPONENT_ID = ComponentId("structure.fibonacci_retracement_level")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.fibonacci_retracement_level")
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
        ParameterFieldSpec("ratio", ParameterType.FLOAT, default=0.618, minimum=0.0),
    )
)
_OUTPUT_SCHEMA = OutputSchema(outputs=(OutputFieldSpec(_VALUE, "float64"),))


class FibonacciRetracementLevelComponent:
    """Causal Fibonacci retracement level of the most recent confirmed swing leg (IDEA-032).

    The "active leg" runs from ``structure.swing``'s latest confirmed
    swing high/low to whichever of the two was confirmed most recently
    (compared by their own ``latest_swing_*_observed_index``): an up-leg
    (``low -> high``) or a down-leg (``high -> low``).

        range = latest_swing_high_level - latest_swing_low_level
        value[up-leg]   = high - ratio * range   -- pulls back toward the low
        value[down-leg] = low  + ratio * range   -- pulls back toward the high

    ``ratio`` defaults to the standard `0.618` retracement level; common
    values also include `0.5`/`0.382`/`0.66` (documented, calibratable, not
    fixed by this component). No zero-denominator case: a linear
    interpolation along ``range``, never a division. ``NaN`` until both a
    swing high and a swing low have been confirmed at least once (no leg
    exists yet).

    Depends on ``structure.swing`` (keyed by ``pivot_range``). Warm-up:
    the dependency's own ``valid_from_index`` (``structure.swing`` itself
    has no fixed warm-up bar count -- its outputs are simply ``NaN`` until
    the first pivot confirms, which this component's own ``NaN``-until-both-
    extremes-exist convention already matches).
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


class NumpyFibonacciRetracementLevelImplementation:
    """NumPy Fibonacci Retracement Level backend."""

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

        # Only one component_dependencies() entry is declared (structure.swing),
        # so its single AnalysisResult carries every level/index output we need.
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
            is_extension=False,
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
    "FibonacciRetracementLevelComponent",
    "NumpyFibonacciRetracementLevelImplementation",
]
