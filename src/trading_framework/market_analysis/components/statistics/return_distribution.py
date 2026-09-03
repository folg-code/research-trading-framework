"""Return Distribution statistics/regime feature component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.kernels import (
    log_returns,
    rolling_skew_and_kurtosis,
)
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

_COMPONENT_ID = ComponentId("statistics.return_distribution")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.return_distribution")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_SKEW_OUTPUT = OutputId("skew")
_EXCESS_KURTOSIS_OUTPUT = OutputId("excess_kurtosis")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(ParameterFieldSpec("period", ParameterType.INT, default=60, minimum=8),)
)
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_SKEW_OUTPUT, "float64"),
        OutputFieldSpec(_EXCESS_KURTOSIS_OUTPUT, "float64"),
    )
)


class ReturnDistributionComponent:
    """Semantic rolling POPULATION Fisher-Pearson skewness and excess kurtosis
    of log returns -- the second of this sprint's two ``statistics.``
    namespace components (D-S051-03), answering the PRD's return-distribution
    open question (PRD Open Question 1).

    Log returns follow the one shared definition used across this sprint's
    catalog (D-S051-03): ``r_t = ln(close_t / close_{t-1})``. Within each
    ``period``-bar window of returns:

        window = returns[i - period + 1 : i + 1]        # `period` values
        mean   = window.mean()
        m2     = ((window - mean) ** 2).mean()            # population variance
        m3     = ((window - mean) ** 3).mean()
        m4     = ((window - mean) ** 4).mean()
        skew[i]            = m3 / m2 ** 1.5                if m2 != 0 else 0.0
        excess_kurtosis[i] = m4 / m2 ** 2 - 3.0             if m2 != 0 else 0.0

    This is the standard ("method of moments") Fisher-Pearson estimator using
    POPULATION moments throughout (``ddof=0``) -- deliberately NOT a
    small-sample bias-corrected variant (e.g. scipy's default ``bias=False``
    adjustment). Determinism and one documented estimator beat matching any
    particular library's default (D-S051-05). Quantile-based (Bowley) skew is
    the recorded fallback if Sprint 052 finds this estimator too noisy for a
    real-data study -- that would be a new component, not a silent change
    (D-S051-03).

    See
    :func:`trading_framework.market_analysis.adapters.numpy.kernels.rolling_skew_and_kurtosis`
    for the exact shared-moment computation.

    Zero-variance convention -- when the window is perfectly flat (``m2 ==
    0.0``), both ``skew`` and ``excess_kurtosis`` are mathematically
    undefined (``0/0``). This component follows the project's ORDINARY
    zero-denominator convention (``candle.wick`` D-S047-10;
    ``trend.ema_distance`` / ``volatility.range_expansion`` /
    ``volatility.relative_volatility`` / ``statistics.return_autocorrelation``
    D-S048-10), NOT ``momentum.stochastic``'s deliberate ``50.0`` divergence
    (D-S051-04): ``0.0`` is the semantically neutral reading for an
    undefined shape, not a fabricated signal.

    WARNING -- short windows on 1-minute bars are outlier-dominated: the
    third and fourth central moments are extremely sensitive to a single
    large return inside the window, so ``skew``/``excess_kurtosis`` computed
    over a small ``period`` on 1m data can be driven almost entirely by one
    bar rather than the window's overall shape. Sprint 052's Wave 0 consumes
    this warning when choosing its evaluation grid/timeframe
    (D-S051-11) -- it is not resolved by this component, only documented by it.

    Warm-up -- ``bars_before`` is ``period`` (in ``close``-bar terms), the
    same warm-up shape as ``volatility.relative_volatility`` (T006) and
    ``statistics.return_autocorrelation`` (T007): ``log_returns`` loses one
    bar to differencing, ``returns[1:]`` is sliced off, a rolling statistic
    over ``period`` return values is computed by
    ``rolling_skew_and_kurtosis`` (first valid at return-index ``period -
    1``), and mapping that back through the ``value[1:] = ...`` assignment
    lands the first valid output bar at close-index ``period`` -- e.g. for
    ``period = 10``: the first full window of return values is
    ``returns[1..10]`` (using ``close[0..10]``), whose rolling-stat output is
    written to ``value[1 + 9] = value[10]``. SPRINT_051.md's task-table
    shorthand ("warm-up `period + 1` asserted") is therefore NOT the value
    implemented here; this docstring documents the reconciliation, following
    the same precedent T007 recorded for its own warm-up (see
    ``ReturnAutocorrelationComponent``'s docstring) -- the discrepancy is
    flagged for the sprint's closure pass (T011), not silently resolved in
    the sprint document.
    """

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = _PARAMETER_SCHEMA
    output_schema = _OUTPUT_SCHEMA

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        period = int(parameters.get("period"))
        return HistoryRequirement(bars_before=period)

    def data_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[DataFieldDependency, ...]:
        return (DataFieldDependency("close"),)

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        return ()


class NumpyReturnDistributionImplementation:
    """NumPy Return Distribution backend."""

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

        returns = log_returns(close)

        skew = np.full(bar_count, np.nan, dtype=np.float64)
        excess_kurtosis = np.full(bar_count, np.nan, dtype=np.float64)
        valid_returns = returns[1:]
        if valid_returns.size > 0:
            skew[1:], excess_kurtosis[1:] = rolling_skew_and_kurtosis(valid_returns, period)

        outputs: dict[OutputId, OutputSeries] = {
            _SKEW_OUTPUT: ndarray_to_output_series(skew),
            _EXCESS_KURTOSIS_OUTPUT: ndarray_to_output_series(excess_kurtosis),
        }
        # Derived from the component's own declared history_requirement, not
        # recomputed from `period` independently -- so a regression in
        # bars_before (the planner's look-back contract) shows up here too,
        # instead of silently diverging from what was actually requested
        # (the RSI lesson, Sprint 051 T003).
        warmup_bars = ReturnDistributionComponent().history_requirement(parameters).bars_before

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


__all__ = ["NumpyReturnDistributionImplementation", "ReturnDistributionComponent"]
