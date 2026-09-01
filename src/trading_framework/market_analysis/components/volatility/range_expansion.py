"""Volatility Range Expansion Market Analysis component."""

from collections.abc import Mapping

import numpy as np

from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.components.volatility.atr import AtrComponent
from trading_framework.market_analysis.components.volatility.true_range import TrueRangeComponent
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

_COMPONENT_ID = ComponentId("volatility.range_expansion")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.range_expansion")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_TRUE_RANGE_ID = ComponentId("volatility.true_range")
_ATR_ID = ComponentId("volatility.atr")
_TRUE_RANGE_VALUE_OUTPUT = OutputId("value")
_ATR_VALUE_OUTPUT = OutputId("value")

_RATIO_OUTPUT = OutputId("ratio")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(ParameterFieldSpec("period", ParameterType.INT, default=14, minimum=1),)
)
_OUTPUT_SCHEMA = OutputSchema(outputs=(OutputFieldSpec(_RATIO_OUTPUT, "float64"),))


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


class RangeExpansionComponent:
    """Dimensionless, causal ratio of a bar's true range to its ATR.

    Depends on ``volatility.true_range`` for the numerator and
    ``volatility.atr`` for the normalizer -- the direct structural sibling of
    ``trend.ema_distance`` (a component that depends on two other components
    rather than raw market data).

    ``ratio = true_range(bar) / atr(period)``

    Warmup inherits the ATR warmup -- ``period - 1`` bars -- since ``ratio``
    is undefined until the normalizer is; outputs are ``NaN`` before that
    index, exactly matching ``AtrComponent``'s own warmup contract.

    Zero/NaN ATR convention, applied per bar -- matching
    ``trend.ema_distance``'s convention exactly (Sprint 048 T009), as locked
    by D-S048-10 ("as C1"):

    * ``atr == 0.0`` (e.g. a flat run of prices): the output is defined as
      ``0.0`` rather than an incidental ``inf``/``NaN`` from the division.
      This mirrors ``candle.wick``'s zero-range-bar convention (D-S047-10) --
      a documented, tested value, not a surprise from IEEE-754 division
      semantics.
    * ``atr`` is ``NaN`` (only possible inside ATR's own warmup, which
      ``valid_from_index`` already excludes): the output propagates as
      ``NaN``, exactly like ``trend.ema_distance``'s warmup handling.
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
        period = int(parameters.get("period"))
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_TRUE_RANGE_ID,
                    parameters=TrueRangeComponent().parameter_schema.canonicalize({}),
                    output_id=_TRUE_RANGE_VALUE_OUTPUT,
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


class NumpyRangeExpansionImplementation:
    """NumPy Range Expansion backend."""

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

        true_range_result = _dependency_result_for(
            workspace.dependency_results,
            component_id=_TRUE_RANGE_ID,
        )
        atr_result = _dependency_result_for(
            workspace.dependency_results,
            component_id=_ATR_ID,
        )
        true_range_values = np.asarray(
            true_range_result.outputs[_TRUE_RANGE_VALUE_OUTPUT].values, dtype=np.float64
        )
        atr_values = np.asarray(atr_result.outputs[_ATR_VALUE_OUTPUT].values, dtype=np.float64)

        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(
                atr_values == 0.0,
                0.0,
                true_range_values / atr_values,
            )

        outputs: dict[OutputId, OutputSeries] = {
            _RATIO_OUTPUT: ndarray_to_output_series(ratio),
        }
        warmup_bars = period - 1
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


__all__ = ["NumpyRangeExpansionImplementation", "RangeExpansionComponent"]
