"""Trend Normalized Slope Market Analysis component."""

from collections.abc import Mapping

import numpy as np

from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.components.trend.slope import SlopeComponent
from trading_framework.market_analysis.components.volatility.relative_volatility import (
    RelativeVolatilityComponent,
)
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
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("trend.normalized_slope")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.normalized_slope")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_SLOPE_ID = ComponentId("trend.slope")
_RELATIVE_VOLATILITY_ID = ComponentId("volatility.relative_volatility")
_SLOPE_OUTPUT = OutputId("value")
_VOLATILITY_VALUE_OUTPUT = OutputId("value")
_VALUE = OutputId("value")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("slope_period", ParameterType.INT, default=20, minimum=2),
        ParameterFieldSpec("volatility_period", ParameterType.INT, default=20, minimum=1),
        ParameterFieldSpec("baseline_period", ParameterType.INT, default=100, minimum=1),
    )
)
_OUTPUT_SCHEMA = OutputSchema(outputs=(OutputFieldSpec(_VALUE, "float64"),))


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


class NormalizedSlopeComponent:
    """Causal OLS slope of close, normalized by a concurrent volatility measure (IDEA-029).

    ``value = trend.slope(slope_period) / volatility.relative_volatility(
    volatility_period, baseline_period).value`` -- the shared normalizer
    decided once for the whole IDEA-029 pack (D-P19-02), not a
    per-component choice. Comparable across different volatility regimes,
    unlike the raw price-per-bar units of ``trend.slope`` alone.

    A real division computed inside ``compute()``, not a DSL composition
    pattern -- the DSL has no arithmetic on an `Operand` (the same
    limitation ``structure.level_distance`` and
    ``volatility.relative_volatility.ratio`` already work around), per
    D-P19-02's Follow-on note.

    Zero-denominator convention: this catalog's ordinary convention
    (D-S048-10) -- when the volatility measure is exactly ``0.0`` (a
    perfectly flat window), ``value = 0.0`` rather than an incidental
    ``inf``/``NaN``. A flat close window also makes the OLS slope itself
    ``0.0``, so this is the internally consistent "no movement, no
    normalized movement" reading, not a fabricated signal.

    Depends on ``trend.slope`` (keyed by ``slope_period``) and
    ``volatility.relative_volatility`` (keyed by ``volatility_period``/
    ``baseline_period``). Warm-up: the later of the two dependencies' own
    ``valid_from_index`` (in practice ``volatility.relative_volatility``'s
    ``baseline_period``, since it enforces `period < baseline_period` and
    `baseline_period` typically exceeds `slope_period`).
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
        slope_period = int(parameters.get("slope_period"))
        volatility_period = int(parameters.get("volatility_period"))
        baseline_period = int(parameters.get("baseline_period"))
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_SLOPE_ID,
                    parameters=SlopeComponent().parameter_schema.canonicalize(
                        {"period": slope_period}
                    ),
                    output_id=_SLOPE_OUTPUT,
                )
            ),
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_RELATIVE_VOLATILITY_ID,
                    parameters=RelativeVolatilityComponent().parameter_schema.canonicalize(
                        {"period": volatility_period, "baseline_period": baseline_period}
                    ),
                    output_id=_VOLATILITY_VALUE_OUTPUT,
                )
            ),
        )


class NumpyNormalizedSlopeImplementation:
    """NumPy Normalized Slope backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        bar_count = len(workspace.market)

        slope_result = _dependency_result_for(workspace.dependency_results, component_id=_SLOPE_ID)
        volatility_result = _dependency_result_for(
            workspace.dependency_results, component_id=_RELATIVE_VOLATILITY_ID
        )

        slope = np.asarray(slope_result.outputs[_SLOPE_OUTPUT].values, dtype=np.float64)
        volatility = np.asarray(
            volatility_result.outputs[_VOLATILITY_VALUE_OUTPUT].values, dtype=np.float64
        )

        with np.errstate(divide="ignore", invalid="ignore"):
            value = np.where(volatility == 0.0, 0.0, slope / volatility)

        warmup_bars = max(
            slope_result.validity.valid_from_index,
            volatility_result.validity.valid_from_index,
        )
        value[:warmup_bars] = np.nan

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
            outputs={_VALUE: ndarray_to_output_series(value)},
            warmup_bars=warmup_bars,
            valid_from_index=warmup_bars,
            bar_count=bar_count,
            workspace=workspace,
        )


__all__ = ["NormalizedSlopeComponent", "NumpyNormalizedSlopeImplementation"]
