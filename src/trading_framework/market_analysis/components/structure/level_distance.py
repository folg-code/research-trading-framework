"""Structure Level Distance Market Analysis component."""

from collections.abc import Mapping

import numpy as np

from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.components.structure.session_range import (
    SessionRangeComponent,
)
from trading_framework.market_analysis.components.volatility.atr import AtrComponent
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

_COMPONENT_ID = ComponentId("structure.level_distance")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.level_distance")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_SESSION_RANGE_ID = ComponentId("structure.session_range")
_ATR_ID = ComponentId("volatility.atr")
_ATR_VALUE_OUTPUT = OutputId("value")
_SESSION_HIGH_OUTPUT = OutputId("session_high")
_SESSION_LOW_OUTPUT = OutputId("session_low")

_DISTANCE_TO_SESSION_HIGH = OutputId("distance_to_session_high_atr")
_DISTANCE_TO_SESSION_LOW = OutputId("distance_to_session_low_atr")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(ParameterFieldSpec("period", ParameterType.INT, default=14, minimum=1),)
)
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_DISTANCE_TO_SESSION_HIGH, "float64"),
        OutputFieldSpec(_DISTANCE_TO_SESSION_LOW, "float64"),
    )
)


def _dependency_result_for(
    dependency_results: Mapping[str, AnalysisResult],
    *,
    component_id: ComponentId,
) -> AnalysisResult:
    for result in dependency_results.values():
        if result.computation_identity.component_id == component_id:
            return result
    raise ComponentValidationError(
        _COMPONENT_ID,
        f"missing dependency result for {component_id}",
    )


class LevelDistanceComponent:
    """ATR-normalized causal distance from close to the running session high/low.

    Depends on ``structure.session_range`` for the *running* (not final)
    session high/low -- that component only ever reports the extremes
    observed up to and including the current bar, so this component never
    leaks the eventual full-session high/low into an earlier bar -- and on
    ``volatility.atr`` for the normalizer.

    ``distance_to_session_high_atr = (session_high - close) / atr``
    ``distance_to_session_low_atr  = (close - session_low) / atr``

    Both are typically non-negative (close sits inside the running session
    range); a value can go negative only if a later intrabar move breaches
    the running extreme before it is folded into the next bar's running
    high/low. Warmup inherits the ATR period: outputs are undefined
    (``NaN``) before ``period - 1`` bars, matching ``volatility.atr``'s own
    ``valid_from_index``. Outside the session (``structure.session_range``
    is ``NaN`` there), both outputs stay ``NaN`` regardless of warmup.
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
        return (DataFieldDependency("close"),)

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        period = int(parameters.get("period"))
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_SESSION_RANGE_ID,
                    parameters=SessionRangeComponent().parameter_schema.canonicalize({}),
                    output_id=_SESSION_HIGH_OUTPUT,
                )
            ),
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_ATR_ID,
                    parameters=AtrComponent().parameter_schema.canonicalize({"period": period}),
                    output_id=_ATR_VALUE_OUTPUT,
                )
            ),
        )


class NumpyLevelDistanceImplementation:
    """NumPy Level Distance backend."""

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

        session_result = _dependency_result_for(
            workspace.dependency_results,
            component_id=_SESSION_RANGE_ID,
        )
        atr_result = _dependency_result_for(
            workspace.dependency_results,
            component_id=_ATR_ID,
        )
        session_high = np.asarray(
            session_result.outputs[_SESSION_HIGH_OUTPUT].values, dtype=np.float64
        )
        session_low = np.asarray(
            session_result.outputs[_SESSION_LOW_OUTPUT].values, dtype=np.float64
        )
        atr_values = np.asarray(atr_result.outputs[_ATR_VALUE_OUTPUT].values, dtype=np.float64)

        with np.errstate(divide="ignore", invalid="ignore"):
            distance_to_high = (session_high - close) / atr_values
            distance_to_low = (close - session_low) / atr_values

        outputs: dict[OutputId, OutputSeries] = {
            _DISTANCE_TO_SESSION_HIGH: ndarray_to_output_series(distance_to_high),
            _DISTANCE_TO_SESSION_LOW: ndarray_to_output_series(distance_to_low),
        }
        warmup_bars = max(period - 1, 0)
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


__all__ = ["LevelDistanceComponent", "NumpyLevelDistanceImplementation"]
