"""Structure Close Reversal Level Market Analysis component."""

import numpy as np

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
from trading_framework.market_analysis.models.result import AnalysisResult, OutputSeries
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("structure.close_reversal_level")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.close_reversal_level")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_REVERSAL_EVENT = OutputId("reversal_event")
_LEVEL = OutputId("level")

_WARMUP_BARS = 2

_PARAMETER_SCHEMA = ParameterSchema(fields=())
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_REVERSAL_EVENT, "float64"),
        OutputFieldSpec(_LEVEL, "float64"),
    )
)


class CloseReversalLevelComponent:
    """Causal level derived from a close-to-close direction reversal ("CISD").

    At bar ``i``, compares the direction of the last close-to-close move
    (``close[i] - close[i-1]``) against the move two bars back
    (``close[i-1] - close[i-2]``). When the two directions are strictly
    opposite (both non-zero, opposite sign), ``reversal_event = 1.0`` and
    ``level = close[i-2]`` -- the close just before the prior directional
    move began, the level this reversal is defined against. ``NaN``/``0.0``
    elsewhere. No warmup beyond this component's own two-bar lookback (no
    ATR or other dependency involved).
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
        return (DataFieldDependency("close"),)

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        return ()


class NumpyCloseReversalLevelImplementation:
    """NumPy Close Reversal Level backend."""

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

        reversal_event = np.zeros(bar_count, dtype=np.float64)
        level = np.full(bar_count, np.nan, dtype=np.float64)
        if bar_count > 2:
            recent_move = close[2:] - close[1:-1]
            prior_move = close[1:-1] - close[:-2]
            recent_direction = np.sign(recent_move)
            prior_direction = np.sign(prior_move)
            is_reversal = (
                (recent_direction != 0.0)
                & (prior_direction != 0.0)
                & (recent_direction == -prior_direction)
            )
            reversal_event[2:] = np.where(is_reversal, 1.0, 0.0)
            level[2:] = np.where(is_reversal, close[:-2], np.nan)

        outputs: dict[OutputId, OutputSeries] = {
            _REVERSAL_EVENT: ndarray_to_output_series(reversal_event),
            _LEVEL: ndarray_to_output_series(level),
        }
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
            warmup_bars=_WARMUP_BARS,
            valid_from_index=_WARMUP_BARS,
            bar_count=bar_count,
            workspace=workspace,
        )


__all__ = ["CloseReversalLevelComponent", "NumpyCloseReversalLevelImplementation"]
