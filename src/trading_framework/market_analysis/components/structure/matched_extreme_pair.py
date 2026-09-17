"""Structure Matched Extreme Pair Market Analysis component."""

from collections.abc import Mapping

import numpy as np

from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.components.structure.swing import SwingStructureComponent
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

_COMPONENT_ID = ComponentId("structure.matched_extreme_pair")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.matched_extreme_pair")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_SWING_ID = ComponentId("structure.swing")
_ATR_ID = ComponentId("volatility.atr")
_ATR_VALUE_OUTPUT = OutputId("value")
_SWING_HIGH_EVENT = OutputId("swing_high_event")
_SWING_LOW_EVENT = OutputId("swing_low_event")
_SWING_HIGH_PRICE = OutputId("swing_high_price")
_SWING_LOW_PRICE = OutputId("swing_low_price")
_LATEST_SWING_HIGH_LEVEL = OutputId("latest_swing_high_level")
_LATEST_SWING_LOW_LEVEL = OutputId("latest_swing_low_level")

_MATCHED_HIGH_EVENT = OutputId("matched_high_event")
_MATCHED_LOW_EVENT = OutputId("matched_low_event")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("pivot_range", ParameterType.INT, default=2, minimum=1),
        ParameterFieldSpec("period", ParameterType.INT, default=14, minimum=1),
        ParameterFieldSpec("tolerance_atr_multiple", ParameterType.FLOAT, default=0.1, minimum=0.0),
    )
)
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_MATCHED_HIGH_EVENT, "float64"),
        OutputFieldSpec(_MATCHED_LOW_EVENT, "float64"),
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


class MatchedExtremePairComponent:
    """Causal two same-type extrema within an ATR tolerance ("equal highs/lows").

    When ``structure.swing`` confirms a new swing high, ``matched_high_event
    = 1.0`` if that new swing high's price is within
    ``tolerance_atr_multiple * atr`` of the *previous* confirmed swing
    high's level -- two highs close enough to be "the same" level.
    ``matched_low_event`` is the mirror for swing lows. The first swing of
    either type has nothing to compare against and never matches.

    Depends on ``structure.swing`` (keyed by ``pivot_range``) and
    ``volatility.atr`` (keyed by ``period``). Warm-up: ``max(0, period - 1)``
    bars -- the ATR's own warmup; a bar within `structure.swing`'s own
    warmup simply has no swing event to test, per that component's own
    contract. Default ``tolerance_atr_multiple = 0.1``, a starting,
    calibratable threshold matching ``structure.range_discontinuity``'s
    own default order of magnitude.
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
        period = int(parameters.get("period"))
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_SWING_ID,
                    parameters=SwingStructureComponent().parameter_schema.canonicalize(
                        {"pivot_range": pivot_range}
                    ),
                    output_id=_SWING_HIGH_EVENT,
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


class NumpyMatchedExtremePairImplementation:
    """NumPy Matched Extreme Pair backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        period = int(parameters.get("period"))
        tolerance_atr_multiple = float(parameters.get("tolerance_atr_multiple"))
        bar_count = len(workspace.market)

        swing_result = _dependency_result_for(workspace.dependency_results, component_id=_SWING_ID)
        atr_result = _dependency_result_for(workspace.dependency_results, component_id=_ATR_ID)

        swing_high_event = np.asarray(
            swing_result.outputs[_SWING_HIGH_EVENT].values, dtype=np.float64
        )
        swing_low_event = np.asarray(
            swing_result.outputs[_SWING_LOW_EVENT].values, dtype=np.float64
        )
        swing_high_price = np.asarray(
            swing_result.outputs[_SWING_HIGH_PRICE].values, dtype=np.float64
        )
        swing_low_price = np.asarray(
            swing_result.outputs[_SWING_LOW_PRICE].values, dtype=np.float64
        )
        latest_swing_high_level = np.asarray(
            swing_result.outputs[_LATEST_SWING_HIGH_LEVEL].values, dtype=np.float64
        )
        latest_swing_low_level = np.asarray(
            swing_result.outputs[_LATEST_SWING_LOW_LEVEL].values, dtype=np.float64
        )
        atr_values = np.asarray(atr_result.outputs[_ATR_VALUE_OUTPUT].values, dtype=np.float64)

        prev_high_level = np.roll(latest_swing_high_level, 1)
        prev_high_level[0] = np.nan
        prev_low_level = np.roll(latest_swing_low_level, 1)
        prev_low_level[0] = np.nan

        with np.errstate(invalid="ignore"):
            tolerance = tolerance_atr_multiple * atr_values
            high_within_tolerance = np.abs(swing_high_price - prev_high_level) <= tolerance
            low_within_tolerance = np.abs(swing_low_price - prev_low_level) <= tolerance

        matched_high = np.where((swing_high_event == 1.0) & high_within_tolerance, 1.0, 0.0)
        matched_low = np.where((swing_low_event == 1.0) & low_within_tolerance, 1.0, 0.0)

        outputs: dict[OutputId, OutputSeries] = {
            _MATCHED_HIGH_EVENT: ndarray_to_output_series(matched_high),
            _MATCHED_LOW_EVENT: ndarray_to_output_series(matched_low),
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


__all__ = ["MatchedExtremePairComponent", "NumpyMatchedExtremePairImplementation"]
