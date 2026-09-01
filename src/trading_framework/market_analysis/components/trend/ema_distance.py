"""Trend EMA Distance Market Analysis component."""

from collections.abc import Mapping

import numpy as np

from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.components.trend.ema import EmaComponent
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

_COMPONENT_ID = ComponentId("trend.ema_distance")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.ema_distance")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_EMA_ID = ComponentId("trend.ema")
_ATR_ID = ComponentId("volatility.atr")
_EMA_VALUE_OUTPUT = OutputId("value")
_ATR_VALUE_OUTPUT = OutputId("value")

_DISTANCE_ATR_OUTPUT = OutputId("distance_atr")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("period", ParameterType.INT, default=20, minimum=1),
        ParameterFieldSpec("atr_period", ParameterType.INT, default=14, minimum=1),
    )
)
_OUTPUT_SCHEMA = OutputSchema(outputs=(OutputFieldSpec(_DISTANCE_ATR_OUTPUT, "float64"),))


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


class EmaDistanceComponent:
    """ATR-normalized, signed, causal distance from close to an EMA.

    Depends on ``trend.ema`` for the mean and ``volatility.atr`` for the
    normalizer -- the direct structural sibling of
    ``structure.level_distance`` (a component that depends on two other
    components rather than raw market data).

    ``distance_atr = (close - ema(period)) / atr(atr_period)``

    Positive values mean close sits above the EMA (in ATR units); negative
    means below. Warmup inherits ``max(EMA warmup, ATR warmup)`` --
    ``max(period, atr_period) - 1`` bars -- since both dependencies must be
    valid before the ratio is defined; outputs are ``NaN`` before that index.

    Zero/NaN ATR convention, applied per bar:

    * ``atr == 0.0`` (e.g. a flat run of prices): the output is defined as
      ``0.0`` rather than an incidental ``inf``/``NaN`` from the division.
      This mirrors ``candle.wick``'s zero-range-bar convention (D-S047-10) --
      a documented, tested value, not a surprise from IEEE-754 division
      semantics.
    * ``atr`` is ``NaN`` (only possible inside ATR's own warmup, which
      ``valid_from_index`` already excludes): the output propagates as
      ``NaN``, exactly like ``structure.level_distance``'s warmup handling.

    This is the convention ``volatility.range_expansion`` (Sprint 048 T010)
    commits to matching for its own ATR denominator.
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
        atr_period = int(parameters.get("atr_period"))
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_EMA_ID,
                    parameters=EmaComponent().parameter_schema.canonicalize({"period": period}),
                    output_id=_EMA_VALUE_OUTPUT,
                )
            ),
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_ATR_ID,
                    parameters=AtrComponent().parameter_schema.canonicalize({"period": atr_period}),
                    output_id=_ATR_VALUE_OUTPUT,
                )
            ),
        )


class NumpyEmaDistanceImplementation:
    """NumPy EMA Distance backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        period = int(parameters.get("period"))
        atr_period = int(parameters.get("atr_period"))
        bar_count = len(workspace.market)
        close = np.asarray(workspace.market.close.values, dtype=np.float64)

        ema_result = _dependency_result_for(
            workspace.dependency_results,
            component_id=_EMA_ID,
        )
        atr_result = _dependency_result_for(
            workspace.dependency_results,
            component_id=_ATR_ID,
        )
        ema_values = np.asarray(ema_result.outputs[_EMA_VALUE_OUTPUT].values, dtype=np.float64)
        atr_values = np.asarray(atr_result.outputs[_ATR_VALUE_OUTPUT].values, dtype=np.float64)

        with np.errstate(divide="ignore", invalid="ignore"):
            distance_atr = np.where(
                atr_values == 0.0,
                0.0,
                (close - ema_values) / atr_values,
            )

        outputs: dict[OutputId, OutputSeries] = {
            _DISTANCE_ATR_OUTPUT: ndarray_to_output_series(distance_atr),
        }
        warmup_bars = max(period - 1, atr_period - 1)
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


__all__ = ["EmaDistanceComponent", "NumpyEmaDistanceImplementation"]
