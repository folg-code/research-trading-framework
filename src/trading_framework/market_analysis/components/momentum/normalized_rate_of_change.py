"""Momentum Normalized Rate Of Change Market Analysis component."""

from collections.abc import Mapping

import numpy as np

from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
)
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

_COMPONENT_ID = ComponentId("momentum.normalized_rate_of_change")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.normalized_rate_of_change")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_RELATIVE_VOLATILITY_ID = ComponentId("volatility.relative_volatility")
_VOLATILITY_VALUE_OUTPUT = OutputId("value")
_VALUE = OutputId("value")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("lookback", ParameterType.INT, default=10, minimum=1),
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


class NormalizedRateOfChangeComponent:
    """Causal log rate of change, normalized by a concurrent volatility measure (IDEA-029).

    ``raw[i] = ln(close[i] / close[i - lookback])``, computed directly here
    (no ``momentum.rate_of_change`` component exists yet to depend on --
    this is a two-line formula, the same "avoid a dependency for arithmetic
    already this simple" reasoning as ``volatility.directional_asymmetry``'s
    own per-bar Parkinson term).

    ``value = raw / volatility.relative_volatility(volatility_period,
    baseline_period).value`` -- the shared normalizer decided once for the
    whole IDEA-029 pack (D-P19-02). A real division computed inside
    ``compute()``, not a DSL composition pattern, per D-P19-02's Follow-on
    note.

    Zero-denominator convention: this catalog's ordinary convention
    (D-S048-10) -- when the volatility measure is exactly ``0.0`` (a
    perfectly flat window), ``value = 0.0``. A flat close window over the
    volatility window also tends to leave ``raw`` at or near ``0.0``, so
    this is an internally consistent "no movement, no normalized movement"
    reading, not a fabricated signal.

    Depends on ``volatility.relative_volatility`` (keyed by
    ``volatility_period``/``baseline_period``) only -- ``raw`` needs only
    raw ``close``. Warm-up: the later of ``lookback`` bars (needed for
    ``raw``) and the volatility dependency's own ``valid_from_index``.
    """

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = _PARAMETER_SCHEMA
    output_schema = _OUTPUT_SCHEMA

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        lookback = int(parameters.get("lookback"))
        return HistoryRequirement(bars_before=lookback)

    def data_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[DataFieldDependency, ...]:
        return (DataFieldDependency("close"),)

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        volatility_period = int(parameters.get("volatility_period"))
        baseline_period = int(parameters.get("baseline_period"))
        return (
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


class NumpyNormalizedRateOfChangeImplementation:
    """NumPy Normalized Rate Of Change backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        lookback = int(parameters.get("lookback"))
        bar_count = len(workspace.market)
        close = np.asarray(workspace.market.close.values, dtype=np.float64)

        raw = np.full(bar_count, np.nan, dtype=np.float64)
        if bar_count > lookback:
            with np.errstate(divide="ignore", invalid="ignore"):
                raw[lookback:] = np.log(close[lookback:] / close[:-lookback])

        volatility_result = _dependency_result_for(
            workspace.dependency_results, component_id=_RELATIVE_VOLATILITY_ID
        )
        volatility = np.asarray(
            volatility_result.outputs[_VOLATILITY_VALUE_OUTPUT].values, dtype=np.float64
        )

        with np.errstate(divide="ignore", invalid="ignore"):
            value = np.where(volatility == 0.0, 0.0, raw / volatility)

        warmup_bars = max(lookback, volatility_result.validity.valid_from_index)
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


__all__ = ["NormalizedRateOfChangeComponent", "NumpyNormalizedRateOfChangeImplementation"]
