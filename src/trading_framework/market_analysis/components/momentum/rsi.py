"""Wilder RSI momentum feature component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.kernels import rsi_wilder
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
from trading_framework.market_analysis.models.parameters import (
    CanonicalParameters,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
)
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("momentum.rsi")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.rsi_wilder")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")
_OUTPUT_ID = OutputId("value")
_PARAMETER_SCHEMA = ParameterSchema(
    fields=(ParameterFieldSpec("period", ParameterType.INT, default=14, minimum=2),)
)
_OUTPUT_SCHEMA = OutputSchema(outputs=(OutputFieldSpec(_OUTPUT_ID, "float64"),))


class RsiComponent:
    """Semantic Wilder RSI feature over canonical close prices.

    ``value`` is a Wilder-smoothed relative strength index in ``[0, 100]``
    (D-S051-05 -- the textbook recursive method, no library-matching). Two
    degenerate windows are defined explicitly rather than left as incidental
    ``inf``/``NaN`` (D-S051-04): a window with gains but no losses yields
    ``100.0``; an entirely flat window (no gains and no losses, so the
    underlying ratio is genuinely undefined) yields the neutral midpoint
    ``50.0``. See
    :func:`trading_framework.market_analysis.adapters.numpy.kernels.rsi_wilder`
    for the exact recursion.
    """

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = _PARAMETER_SCHEMA
    output_schema = _OUTPUT_SCHEMA

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        return HistoryRequirement(bars_before=int(parameters.get("period")))

    def data_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[DataFieldDependency, ...]:
        return (DataFieldDependency("close"),)

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        return ()


class NumpyRsiImplementation:
    """NumPy Wilder RSI backend."""

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
        close = np.asarray(workspace.market.close.values, dtype=np.float64)
        values = rsi_wilder(close, period)
        # Derived from the component's own declared history_requirement,
        # not re-computed from `period` independently -- so a regression in
        # bars_before (the planner's look-back contract) shows up here too,
        # instead of silently diverging from what was actually requested.
        warmup_bars = RsiComponent().history_requirement(parameters).bars_before
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
            warmup_bars=warmup_bars,
            valid_from_index=warmup_bars,
            bar_count=bar_count,
            workspace=workspace,
        )


__all__ = ["NumpyRsiImplementation", "RsiComponent"]
