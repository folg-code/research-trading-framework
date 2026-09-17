"""Volatility Directional Asymmetry Market Analysis component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.directional_asymmetry import (
    directional_asymmetry,
)
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
from trading_framework.market_analysis.models.parameters import (
    CanonicalParameters,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
)
from trading_framework.market_analysis.models.result import AnalysisResult, OutputSeries
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("volatility.directional_asymmetry")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.directional_asymmetry")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_UP_VOLATILITY = OutputId("up_volatility")
_DOWN_VOLATILITY = OutputId("down_volatility")
_ASYMMETRY = OutputId("asymmetry")

# Same Parkinson single-bar term as volatility.range_based_variance's default
# method. Computed directly here (not via a ComponentDependency) because
# this component needs the *per-bar* term to split by direction within its
# own rolling window, not a finished rolling average -- depending on that
# component would not save real work, only add a dependency for a two-line
# formula (IDEA-028's own "avoid wrapping arithmetic" concern, applied to
# the dependency graph rather than the DSL).
_PARKINSON_CONSTANT = 1.0 / (4.0 * np.log(2.0))

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(ParameterFieldSpec("period", ParameterType.INT, default=20, minimum=2),)
)
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_UP_VOLATILITY, "float64"),
        OutputFieldSpec(_DOWN_VOLATILITY, "float64"),
        OutputFieldSpec(_ASYMMETRY, "float64"),
    )
)


class DirectionalAsymmetryComponent:
    """Causal up-bar vs. down-bar range-based volatility asymmetry.

    Within a rolling ``period``-bar window, splits bars into "up"
    (``close[j] > close[j-1]``) and "down" (``close[j] < close[j-1]``),
    averages each side's Parkinson single-bar variance term separately,
    and reports the square root of each (``up_volatility``,
    ``down_volatility``) plus ``asymmetry = ln(up_volatility /
    down_volatility)``. A window with no bars of one side yields ``NaN``
    for that side and for ``asymmetry`` -- an asymmetry needs both sides.
    ``down_volatility == 0.0`` (down bars all flat-range) yields
    ``asymmetry = 0.0``, the ordinary zero-denominator convention.

    Warm-up: ``period - 1`` bars, same as
    ``volatility.range_based_variance``. No dependency: computes its own
    per-bar Parkinson term directly (see module comment).
    """

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = _PARAMETER_SCHEMA
    output_schema = _OUTPUT_SCHEMA

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        period = int(parameters.get("period"))
        return HistoryRequirement(bars_before=max(period - 1, 0))

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


class NumpyDirectionalAsymmetryImplementation:
    """NumPy Directional Asymmetry backend."""

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
        high = np.asarray(workspace.market.high.values, dtype=np.float64)
        low = np.asarray(workspace.market.low.values, dtype=np.float64)
        close = np.asarray(workspace.market.close.values, dtype=np.float64)

        per_bar_variance_term = _PARKINSON_CONSTANT * (np.log(high / low) ** 2)
        arrays = directional_asymmetry(per_bar_variance_term, close, period=period)

        outputs: dict[OutputId, OutputSeries] = {
            _UP_VOLATILITY: ndarray_to_output_series(arrays.up_volatility),
            _DOWN_VOLATILITY: ndarray_to_output_series(arrays.down_volatility),
            _ASYMMETRY: ndarray_to_output_series(arrays.asymmetry),
        }
        warmup_bars = max(period - 1, 0)
        return build_analysis_result(
            context=context,
            component_id=_COMPONENT_ID,
            component_version=_COMPONENT_VERSION,
            implementation_id=_IMPLEMENTATION_ID,
            implementation_version=_IMPLEMENTATION_VERSION,
            parameters=parameters,
            dependency_keys=(),
            output_schema=_OUTPUT_SCHEMA,
            outputs=outputs,
            warmup_bars=warmup_bars,
            valid_from_index=warmup_bars,
            bar_count=bar_count,
            workspace=workspace,
        )


__all__ = ["DirectionalAsymmetryComponent", "NumpyDirectionalAsymmetryImplementation"]
