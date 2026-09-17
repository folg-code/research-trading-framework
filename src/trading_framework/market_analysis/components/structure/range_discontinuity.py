"""Structure Range Discontinuity Market Analysis component."""

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

_COMPONENT_ID = ComponentId("structure.range_discontinuity")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.range_discontinuity")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_ATR_ID = ComponentId("volatility.atr")
_ATR_VALUE_OUTPUT = OutputId("value")

_GAP_UP_EVENT = OutputId("gap_up_event")
_GAP_DOWN_EVENT = OutputId("gap_down_event")

_WARMUP_BARS = 2

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("period", ParameterType.INT, default=14, minimum=1),
        ParameterFieldSpec("min_gap_atr_multiple", ParameterType.FLOAT, default=0.1, minimum=0.0),
    )
)
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_GAP_UP_EVENT, "float64"),
        OutputFieldSpec(_GAP_DOWN_EVENT, "float64"),
    )
)


class RangeDiscontinuityComponent:
    """Causal three-bar range gap in the direction of a move ("fair value gap").

    ``gap_up_event = 1.0`` at bar ``i`` when ``low[i] - high[i-2]`` exceeds
    ``min_gap_atr_multiple * atr[i]`` -- the current bar's range never
    overlaps the range from two bars back, in the up direction.
    ``gap_down_event`` is the mirror: ``low[i-2] - high[i]`` exceeds the
    same threshold. Distinct from ``structure.opening_gap``, which is an
    open-vs-prior-close gap, not a three-bar range gap.

    Depends on ``volatility.atr`` keyed by ``period``, same pattern as
    ``structure.level_distance``/``structure.opening_gap``. Warm-up:
    ``max(2, period - 1)`` bars (this component's own two-bar lookback, or
    the wider ATR warmup). Default ``min_gap_atr_multiple = 0.1``
    (D-P19-05): a starting, calibratable threshold, not a fixed constant.
    A zero ATR (perfectly flat recent bars) collapses the threshold to
    zero, so any non-overlapping three-bar range would trivially qualify
    -- an extreme, unlikely-in-real-data degenerate case, not
    special-cased.
    """

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
        return (DataFieldDependency("high"), DataFieldDependency("low"))

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


class NumpyRangeDiscontinuityImplementation:
    """NumPy Range Discontinuity backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        period = int(parameters.get("period"))
        min_gap_atr_multiple = float(parameters.get("min_gap_atr_multiple"))
        bar_count = len(workspace.market)
        high = np.asarray(workspace.market.high.values, dtype=np.float64)
        low = np.asarray(workspace.market.low.values, dtype=np.float64)

        atr_values = dependency_results_values(
            workspace.dependency_results,
            output_id=_ATR_VALUE_OUTPUT,
        )

        gap_up = np.zeros(bar_count, dtype=np.float64)
        gap_down = np.zeros(bar_count, dtype=np.float64)
        if bar_count > 2:
            threshold = min_gap_atr_multiple * atr_values[2:]
            with np.errstate(invalid="ignore"):
                up_size = low[2:] - high[:-2]
                down_size = low[:-2] - high[2:]
                gap_up[2:] = np.where(up_size > threshold, 1.0, 0.0)
                gap_down[2:] = np.where(down_size > threshold, 1.0, 0.0)

        outputs: dict[OutputId, OutputSeries] = {
            _GAP_UP_EVENT: ndarray_to_output_series(gap_up),
            _GAP_DOWN_EVENT: ndarray_to_output_series(gap_down),
        }
        warmup_bars = max(_WARMUP_BARS, period - 1)
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


__all__ = ["NumpyRangeDiscontinuityImplementation", "RangeDiscontinuityComponent"]
