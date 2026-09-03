"""Return Autocorrelation statistics/regime feature component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.kernels import (
    log_returns,
    rolling_lagged_pearson_correlation,
)
from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
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
from trading_framework.market_analysis.models.outputs import OutputFieldSpec, OutputId, OutputSchema
from trading_framework.market_analysis.models.parameters import (
    CanonicalParameters,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
)
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("statistics.return_autocorrelation")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.return_autocorrelation")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_VALUE_OUTPUT = OutputId("value")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("period", ParameterType.INT, default=60, minimum=8),
        ParameterFieldSpec("lag", ParameterType.INT, default=1, minimum=1),
    )
)
_OUTPUT_SCHEMA = OutputSchema(outputs=(OutputFieldSpec(_VALUE_OUTPUT, "float64"),))


def _validate_lag(period: int, lag: int) -> None:
    if lag >= period - 1:
        raise ComponentValidationError(
            _COMPONENT_ID,
            f"lag ({lag}) must be less than period - 1 ({period - 1})",
        )


class ReturnAutocorrelationComponent:
    """Semantic rolling lag-``k`` autocorrelation of log returns -- the first
    of this sprint's two ``statistics.`` namespace components (D-S051-03),
    proving a new dotted namespace the same way ``candle.`` was introduced in
    Sprint 047 (no ADR needed, D-S051-10).

    Log returns follow the one shared definition used across this sprint's
    catalog (D-S051-03): ``r_t = ln(close_t / close_{t-1})``. Within each
    ``period``-bar window of returns, the window is split into an unshifted
    prefix and a lag-``lag`` shifted suffix, and ``value`` is the standard
    (population) Pearson correlation between the two:

        window = returns[i - period + 1 : i + 1]      # `period` values
        x = window[: period - lag]                     # unshifted
        y = window[lag:]                                # lag-shifted
        value[i] = cov(x, y) / (std(x) * std(y))        # population moments

    See
    :func:`trading_framework.market_analysis.adapters.numpy.kernels.rolling_lagged_pearson_correlation`
    for the exact computation.

    Zero-variance convention -- when either ``x`` or ``y`` is a constant
    sub-window (a degenerate, effectively flat window -- e.g. a run of
    identical prices), the correlation is mathematically undefined
    (``0/0``). This component follows the project's ORDINARY
    zero-denominator convention (``candle.wick`` D-S047-10;
    ``trend.ema_distance`` / ``volatility.range_expansion`` /
    ``volatility.relative_volatility`` D-S048-10), NOT
    ``momentum.stochastic``'s deliberate ``50.0`` divergence (D-S051-04):
    ``0.0`` ("no defined relationship") is the semantically correct neutral
    reading for a degenerate correlation window, not a fabricated signal.

    Validation -- ``lag`` must satisfy ``lag < period - 1`` so that ``x`` and
    ``y`` each retain at least 2 points (the minimum a correlation needs to
    be computable at all); violating it raises ``ComponentValidationError``
    naming both values.

    Warm-up -- ``bars_before`` is ``period`` (in ``close``-bar terms), NOT
    ``period + lag``. This is a DELIBERATE, DOCUMENTED reconciliation of
    SPRINT_051.md's task-table shorthand ("warm-up `period + lag` asserted")
    against the precise formula above (also SPRINT_051.md's own source of
    truth): the correlation window already contains exactly ``period``
    return values in total: ``lag`` only determines how that ONE fixed-size
    window is split into its unshifted/lag-shifted halves -- it does not
    require any additional bars of history beyond ``period``. This mirrors
    ``volatility.relative_volatility``'s ``value`` output, whose own warm-up
    is likewise ``period`` (not ``period + 1``, despite ``log_returns``
    losing one bar to differencing) -- that loss is already absorbed into
    the ``period``-bar warm-up count. See the kernel's own docstring for the
    same reasoning.
    """

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = _PARAMETER_SCHEMA
    output_schema = _OUTPUT_SCHEMA

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        period = int(parameters.get("period"))
        lag = int(parameters.get("lag"))
        _validate_lag(period, lag)
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


class NumpyReturnAutocorrelationImplementation:
    """NumPy Return Autocorrelation backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        period = int(parameters.get("period"))
        lag = int(parameters.get("lag"))
        _validate_lag(period, lag)
        bar_count = len(workspace.market)
        close = np.asarray(workspace.market.close.values, dtype=np.float64)

        returns = log_returns(close)

        value = np.full(bar_count, np.nan, dtype=np.float64)
        valid_returns = returns[1:]
        if valid_returns.size > 0:
            value[1:] = rolling_lagged_pearson_correlation(valid_returns, period, lag)

        outputs = {_VALUE_OUTPUT: ndarray_to_output_series(value)}
        # Derived from the component's own declared history_requirement, not
        # recomputed from `period`/`lag` independently -- so a regression in
        # bars_before (the planner's look-back contract) shows up here too,
        # instead of silently diverging from what was actually requested
        # (the RSI lesson, Sprint 051 T003).
        warmup_bars = ReturnAutocorrelationComponent().history_requirement(parameters).bars_before

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


__all__ = ["NumpyReturnAutocorrelationImplementation", "ReturnAutocorrelationComponent"]
