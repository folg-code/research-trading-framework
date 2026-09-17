"""Volatility Regime State Market Analysis component."""

from collections.abc import Mapping

import numpy as np

from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
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
    OutputGroup,
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

_COMPONENT_ID = ComponentId("volatility.regime_state")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.regime_state")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")
_ATR_ID = ComponentId("volatility.atr")
_ATR_VALUE_OUTPUT = OutputId("value")

_STATE_OUTPUT = OutputId("state")
_RATIO_OUTPUT = OutputId("ratio")

_COMPRESSION = -1.0
_BALANCED = 0.0
_EXPANSION = 1.0

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("fast_period", ParameterType.INT, default=5, minimum=1),
        ParameterFieldSpec("slow_period", ParameterType.INT, default=20, minimum=1),
        ParameterFieldSpec("compression_threshold", ParameterType.FLOAT, default=0.85, minimum=0.0),
        ParameterFieldSpec("expansion_threshold", ParameterType.FLOAT, default=1.15, minimum=0.0),
    )
)
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_STATE_OUTPUT, "float64", group=OutputGroup.CORE),
        OutputFieldSpec(_RATIO_OUTPUT, "float64", group=OutputGroup.DIAGNOSTIC),
    )
)


def _validate_periods(fast_period: int, slow_period: int) -> None:
    if fast_period >= slow_period:
        raise ComponentValidationError(
            _COMPONENT_ID,
            f"fast_period ({fast_period}) must be less than slow_period ({slow_period})",
        )


def _atr_result_for_period(
    dependency_results: Mapping[str, AnalysisResult],
    *,
    period: int,
) -> AnalysisResult:
    for result in dependency_results.values():
        identity = result.computation_identity
        if identity.component_id == _ATR_ID and identity.parameters.get("period") == period:
            return result
    raise ComponentValidationError(
        _COMPONENT_ID,
        f"missing volatility.atr dependency result for period={period}",
    )


class RegimeStateComponent:
    """Causal three-state volatility regime from a fast/slow ATR ratio.

    ``ratio = atr(fast_period) / atr(slow_period)``. ``state = -1.0``
    ("compression") when ``ratio < compression_threshold``, ``1.0``
    ("expansion") when ``ratio > expansion_threshold``, otherwise ``0.0``
    ("balanced"). Distinct from the existing ``volatility.state`` (a
    single-ATR/fixed-threshold LOW/HIGH split) -- this is a second,
    ratio-based volatility vocabulary, not a replacement.

    Requires ``fast_period < slow_period`` (rejected otherwise, matching
    ``momentum.macd``'s convention): the ratio is only meaningful as "fast
    volatility relative to its own slower baseline" when the two windows
    are actually ordered.

    Zero-denominator convention: when the slow ATR is exactly ``0.0`` (no
    true range at all in that window -- the flattest possible market),
    ``ratio = 0.0`` rather than ``NaN``. This is deliberately NOT this
    catalog's ordinary "0.0 is neutral" convention -- here ``0.0`` is the
    genuinely most-compressed reading, and a completely flat slow window is
    itself the extreme compression case, so it falls out of the same
    ``< compression_threshold`` comparison as any other low ratio.

    Depends on two ``volatility.atr`` outputs (one per period), the
    direct structural sibling of ``momentum.macd``. Warm-up is derived from
    the dependency results' own ``valid_from_index`` (the slower ATR's,
    since ``fast_period < slow_period`` is enforced) rather than
    recomputed independently from the parameters.
    """

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.STATE
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
        fast_period = int(parameters.get("fast_period"))
        slow_period = int(parameters.get("slow_period"))
        _validate_periods(fast_period, slow_period)
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_ATR_ID,
                    parameters=AtrComponent().parameter_schema.canonicalize(
                        {"period": fast_period}
                    ),
                    output_id=_ATR_VALUE_OUTPUT,
                )
            ),
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_ATR_ID,
                    parameters=AtrComponent().parameter_schema.canonicalize(
                        {"period": slow_period}
                    ),
                    output_id=_ATR_VALUE_OUTPUT,
                )
            ),
        )


class NumpyRegimeStateImplementation:
    """NumPy Regime State backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        fast_period = int(parameters.get("fast_period"))
        slow_period = int(parameters.get("slow_period"))
        _validate_periods(fast_period, slow_period)
        compression_threshold = float(parameters.get("compression_threshold"))
        expansion_threshold = float(parameters.get("expansion_threshold"))
        bar_count = len(workspace.market)

        fast_result = _atr_result_for_period(workspace.dependency_results, period=fast_period)
        slow_result = _atr_result_for_period(workspace.dependency_results, period=slow_period)
        fast_atr = np.asarray(fast_result.outputs[_ATR_VALUE_OUTPUT].values, dtype=np.float64)
        slow_atr = np.asarray(slow_result.outputs[_ATR_VALUE_OUTPUT].values, dtype=np.float64)

        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(slow_atr == 0.0, 0.0, fast_atr / slow_atr)
        state = np.where(
            ratio < compression_threshold,
            _COMPRESSION,
            np.where(ratio > expansion_threshold, _EXPANSION, _BALANCED),
        )

        warmup_bars = max(
            fast_result.validity.valid_from_index,
            slow_result.validity.valid_from_index,
        )
        ratio[:warmup_bars] = np.nan
        state[:warmup_bars] = np.nan

        outputs: dict[OutputId, OutputSeries] = {
            _STATE_OUTPUT: ndarray_to_output_series(state),
            _RATIO_OUTPUT: ndarray_to_output_series(ratio),
        }
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


__all__ = ["NumpyRegimeStateImplementation", "RegimeStateComponent"]
