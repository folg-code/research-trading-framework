"""Stochastic Oscillator momentum feature component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.kernels import sma, stochastic_percent_k
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
from trading_framework.market_analysis.models.parameters import (
    CanonicalParameters,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
)
from trading_framework.market_analysis.models.result import AnalysisResult, OutputSeries
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("momentum.stochastic")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.stochastic")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_K_OUTPUT = OutputId("k")
_D_OUTPUT = OutputId("d")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("period", ParameterType.INT, default=14, minimum=2),
        ParameterFieldSpec("smoothing_period", ParameterType.INT, default=3, minimum=1),
    )
)
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_K_OUTPUT, "float64"),
        OutputFieldSpec(_D_OUTPUT, "float64"),
    )
)


class StochasticComponent:
    """Semantic Stochastic Oscillator feature over canonical high/low/close.

    ``k`` is the rolling %K over the ``period``-bar high/low range:

        %K = (close - min(low, period)) / (max(high, period) - min(low, period)) * 100

    ``d`` is the simple moving average of ``k`` over ``smoothing_period``, the
    direct multi-output sibling of ``momentum.macd`` (``line``/``signal``/
    ``histogram``): one dotted namespace, several outputs of one causal
    computation, rather than a single "stochastic()" bundle.

    Zero-range window convention -- a DELIBERATE DIVERGENCE from this
    project's usual 0.0-on-zero-denominator convention (``candle.wick``
    D-S047-10; ``trend.ema_distance`` / ``volatility.range_expansion``
    D-S048-10). When a window is genuinely flat
    (``max(high window) == min(low window)``), ``k`` is defined as ``50.0``
    (the neutral midpoint), NOT ``0.0``. Reason (D-S051-04): %K == 0.0
    already means "close sits at the window's low" -- a real, actionable
    signal. Emitting ``0.0`` for a flat window would fabricate that same
    false "close is at the low" signal rather than merely avoid an
    ``inf``/``NaN`` from IEEE-754 division. **Do not "fix" this back to
    0.0 as an apparent inconsistency** -- this is D-S051-04 in
    ``docs/planning/sprints/S051_WAVE0_DECISIONS.md``, and every other
    degenerate-window convention in this catalog keeps ``0.0`` on purpose;
    only ``momentum.stochastic`` diverges, for the reason above.

    Warmup: ``k`` needs a full ``period``-bar rolling window (valid from
    index ``period - 1``); ``d`` additionally needs ``smoothing_period - 1``
    further valid ``k`` bars before it (an SMA needs a full window), so the
    component's overall warmup -- and the ``valid_from_index`` reported for
    both outputs, matching ``momentum.macd``'s shared-validity precedent --
    is ``period + smoothing_period - 2``.
    """

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = _PARAMETER_SCHEMA
    output_schema = _OUTPUT_SCHEMA

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        period = int(parameters.get("period"))
        smoothing_period = int(parameters.get("smoothing_period"))
        return HistoryRequirement(bars_before=period + smoothing_period - 2)

    def data_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[DataFieldDependency, ...]:
        return (
            DataFieldDependency("high"),
            DataFieldDependency("low"),
            DataFieldDependency("close"),
        )

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        return ()


class NumpyStochasticImplementation:
    """NumPy Stochastic Oscillator backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        period = int(parameters.get("period"))
        smoothing_period = int(parameters.get("smoothing_period"))
        bar_count = len(workspace.market)

        high = np.asarray(workspace.market.high.values, dtype=np.float64)
        low = np.asarray(workspace.market.low.values, dtype=np.float64)
        close = np.asarray(workspace.market.close.values, dtype=np.float64)

        k = stochastic_percent_k(high, low, close, period)

        k_valid_from = period - 1
        d = np.full(bar_count, np.nan, dtype=np.float64)
        valid_k = k[k_valid_from:]
        if valid_k.size > 0:
            d[k_valid_from:] = sma(valid_k, smoothing_period)

        # Derived from the component's own declared history_requirement, not
        # recomputed from `period`/`smoothing_period` independently -- so a
        # regression in `bars_before` (the planner's look-back contract)
        # shows up here too, instead of silently diverging from what was
        # actually requested (the RSI lesson, Sprint 051 T003).
        warmup_bars = StochasticComponent().history_requirement(parameters).bars_before

        outputs: dict[OutputId, OutputSeries] = {
            _K_OUTPUT: ndarray_to_output_series(k),
            _D_OUTPUT: ndarray_to_output_series(d),
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
            warmup_bars=warmup_bars,
            valid_from_index=warmup_bars,
            bar_count=bar_count,
            workspace=workspace,
        )


__all__ = ["NumpyStochasticImplementation", "StochasticComponent"]
