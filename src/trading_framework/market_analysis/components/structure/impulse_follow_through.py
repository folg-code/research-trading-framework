"""Structure Impulse Follow-Through Market Analysis component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.impulse import impulse_directions
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

_COMPONENT_ID = ComponentId("structure.impulse_follow_through")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.impulse_follow_through")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_ATR_ID = ComponentId("volatility.atr")
_ATR_VALUE_OUTPUT = OutputId("value")

_FOLLOW_THROUGH_ATR = OutputId("follow_through_atr")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("period", ParameterType.INT, default=14, minimum=1),
        ParameterFieldSpec("impulse_atr_multiple", ParameterType.FLOAT, default=1.5, minimum=0.0),
        ParameterFieldSpec("lookahead_bars", ParameterType.INT, default=5, minimum=1),
    )
)
_OUTPUT_SCHEMA = OutputSchema(outputs=(OutputFieldSpec(_FOLLOW_THROUGH_ATR, "float64"),))


class ImpulseFollowThroughComponent:
    """Retrospective ATR-normalized strength of continuation after an impulse bar.

    The strength-of-continuation counterpart to
    ``structure.impulse_origin_range``: for each impulsive bar ``i`` (body
    ``|close - open|`` at least ``impulse_atr_multiple`` times the
    concurrent ATR), ``follow_through_atr`` is the directional extreme move
    over the next ``lookahead_bars`` bars, normalized by ATR at bar ``i``:

    ``(max(high[i+1..i+lookahead_bars]) - close[i]) / atr[i]`` for a
    bullish impulse, ``(close[i] - min(low[i+1..i+lookahead_bars])) / atr[i]``
    for a bearish one.

    ``NaN`` on every non-impulsive bar, and on an impulsive bar within
    ``lookahead_bars`` of the end of the dataset (not enough future bars to
    confirm) -- an ordinary within-range ``NaN``, not a warmup boundary.

    **Causality: RETROSPECTIVE.** This component's value at bar ``i``
    depends on bars strictly after ``i`` -- it is a research-only measure
    of what happened next, never a live/causal signal. Depends on
    ``volatility.atr`` keyed by ``period``. Default
    ``impulse_atr_multiple = 1.5`` (D-P19-05, matching
    ``structure.impulse_origin_range``'s own default) and
    ``lookahead_bars = 5`` -- both calibratable starting points.
    """

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.FEATURE
    causality = Causality.RETROSPECTIVE
    parameter_schema = _PARAMETER_SCHEMA
    output_schema = _OUTPUT_SCHEMA

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        return HistoryRequirement(bars_before=0)

    def data_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[DataFieldDependency, ...]:
        return (
            DataFieldDependency("open"),
            DataFieldDependency("high"),
            DataFieldDependency("low"),
            DataFieldDependency("close"),
        )

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


class NumpyImpulseFollowThroughImplementation:
    """NumPy Impulse Follow-Through backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        period = int(parameters.get("period"))
        impulse_atr_multiple = float(parameters.get("impulse_atr_multiple"))
        lookahead_bars = int(parameters.get("lookahead_bars"))
        bar_count = len(workspace.market)
        open_ = np.asarray(workspace.market.open.values, dtype=np.float64)
        high = np.asarray(workspace.market.high.values, dtype=np.float64)
        low = np.asarray(workspace.market.low.values, dtype=np.float64)
        close = np.asarray(workspace.market.close.values, dtype=np.float64)

        atr_values = dependency_results_values(
            workspace.dependency_results,
            output_id=_ATR_VALUE_OUTPUT,
        )
        direction = impulse_directions(
            open_, close, atr_values, impulse_atr_multiple=impulse_atr_multiple
        )

        follow_through = np.full(bar_count, np.nan, dtype=np.float64)
        for index in range(bar_count - lookahead_bars):
            if direction[index] == 0.0:
                continue
            window_high = np.max(high[index + 1 : index + 1 + lookahead_bars])
            window_low = np.min(low[index + 1 : index + 1 + lookahead_bars])
            move = window_high - close[index] if direction[index] > 0 else close[index] - window_low
            with np.errstate(divide="ignore", invalid="ignore"):
                follow_through[index] = move / atr_values[index]

        outputs: dict[OutputId, OutputSeries] = {
            _FOLLOW_THROUGH_ATR: ndarray_to_output_series(follow_through),
        }
        warmup_bars = max(0, period - 1)
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


__all__ = ["ImpulseFollowThroughComponent", "NumpyImpulseFollowThroughImplementation"]
