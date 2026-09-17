"""Candle Reversal Pattern Market Analysis component."""

from collections.abc import Mapping

import numpy as np

from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.adapters.numpy.reversal_pattern import reversal_pattern
from trading_framework.market_analysis.components.candle.wick import CandleWickComponent
from trading_framework.market_analysis.components.structure.swing import SwingStructureComponent
from trading_framework.market_analysis.errors import ComponentValidationError
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

_COMPONENT_ID = ComponentId("candle.reversal_pattern")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.reversal_pattern")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_SWING_ID = ComponentId("structure.swing")
_WICK_ID = ComponentId("candle.wick")
_LATEST_SWING_HIGH_LEVEL = OutputId("latest_swing_high_level")
_LATEST_SWING_LOW_LEVEL = OutputId("latest_swing_low_level")
_UPPER_WICK_RATIO = OutputId("upper_wick_ratio")
_LOWER_WICK_RATIO = OutputId("lower_wick_ratio")
_BODY_RATIO = OutputId("body_ratio")

_BULLISH_PATTERN = OutputId("bullish_pattern")
_BEARISH_PATTERN = OutputId("bearish_pattern")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("pivot_range", ParameterType.INT, default=2, minimum=1),
        ParameterFieldSpec("wick_ratio_threshold", ParameterType.FLOAT, default=2.0, minimum=0.0),
    )
)
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_BULLISH_PATTERN, "float64"),
        OutputFieldSpec(_BEARISH_PATTERN, "float64"),
    )
)


def _result_for(
    dependency_results: Mapping[str, AnalysisResult],
    *,
    component_id: ComponentId,
) -> AnalysisResult:
    for result in dependency_results.values():
        if result.computation_identity.component_id == component_id:
            return result
    raise ComponentValidationError(
        _COMPONENT_ID,
        f"missing {component_id.value} dependency result",
    )


class ReversalPatternComponent:
    """Causal, priority-ordered per-bar/side candle reversal pattern label (D-P19-05).

    ``bullish_pattern``/``bearish_pattern`` each carry ONE label per bar,
    evaluated in fixed priority order (first match wins):

    1. ``engulfing`` (code ``1.0``) -- the current bar's body fully
       contains the prior bar's body and the two bars close in opposite
       directions.
    2. ``level_close_reversal`` (code ``2.0``) -- the bar pierces
       ``structure.swing``'s latest confirmed level (as of the *prior*
       bar) but closes back on the origin side, same-bar (not a pending
       multi-bar event like ``structure.level_sweep_rejection``).
    3. ``rejection_wick`` (code ``3.0``) -- a hammer-style single-bar
       rejection: the rejecting wick is at least ``wick_ratio_threshold``
       times the body (via ``candle.wick``'s ratios), with the opposite
       wick no larger than the body. A zero-body (doji) bar never
       qualifies.
    4. ``none`` (code ``0.0``) -- an explicit, always-assigned label for a
       fully-evaluated bar where nothing matched; distinct from ``NaN``,
       which means "not yet warmed up," not "evaluated, no pattern."

    Depends on ``structure.swing`` (keyed by ``pivot_range``) and
    ``candle.wick`` (no parameters). Warm-up: 1 bar -- ``engulfing`` needs
    a prior bar to compare against; once that exists every later bar
    receives a real label even on bars where the swing level is still
    ``NaN`` (that just means ``level_close_reversal`` cannot fire, not
    that the whole component is unwarmed).
    """

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = _PARAMETER_SCHEMA
    output_schema = _OUTPUT_SCHEMA

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        return HistoryRequirement(bars_before=1)

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
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_WICK_ID,
                    parameters=CandleWickComponent().parameter_schema.canonicalize({}),
                    output_id=_UPPER_WICK_RATIO,
                )
            ),
        )


class NumpyReversalPatternImplementation:
    """NumPy Candle Reversal Pattern backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        wick_ratio_threshold = float(parameters.get("wick_ratio_threshold"))
        bar_count = len(workspace.market)
        open_ = np.asarray(workspace.market.open.values, dtype=np.float64)
        high = np.asarray(workspace.market.high.values, dtype=np.float64)
        low = np.asarray(workspace.market.low.values, dtype=np.float64)
        close = np.asarray(workspace.market.close.values, dtype=np.float64)

        swing_result = _result_for(workspace.dependency_results, component_id=_SWING_ID)
        wick_result = _result_for(workspace.dependency_results, component_id=_WICK_ID)
        latest_swing_high_level = np.asarray(
            swing_result.outputs[_LATEST_SWING_HIGH_LEVEL].values, dtype=np.float64
        )
        latest_swing_low_level = np.asarray(
            swing_result.outputs[_LATEST_SWING_LOW_LEVEL].values, dtype=np.float64
        )
        upper_wick_ratio = np.asarray(
            wick_result.outputs[_UPPER_WICK_RATIO].values, dtype=np.float64
        )
        lower_wick_ratio = np.asarray(
            wick_result.outputs[_LOWER_WICK_RATIO].values, dtype=np.float64
        )
        body_ratio = np.asarray(wick_result.outputs[_BODY_RATIO].values, dtype=np.float64)

        arrays = reversal_pattern(
            open_,
            high,
            low,
            close,
            latest_swing_high_level,
            latest_swing_low_level,
            upper_wick_ratio,
            lower_wick_ratio,
            body_ratio,
            wick_ratio_threshold=wick_ratio_threshold,
        )

        outputs: dict[OutputId, OutputSeries] = {
            _BULLISH_PATTERN: ndarray_to_output_series(arrays.bullish_pattern),
            _BEARISH_PATTERN: ndarray_to_output_series(arrays.bearish_pattern),
        }
        warmup_bars = 1
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


__all__ = ["NumpyReversalPatternImplementation", "ReversalPatternComponent"]
