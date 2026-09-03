"""Relative Volatility Market Analysis component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.kernels import (
    log_returns,
    rolling_population_stdev,
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
from trading_framework.market_analysis.models.result import AnalysisResult, OutputSeries
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("volatility.relative_volatility")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.relative_volatility")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_VALUE_OUTPUT = OutputId("value")
_RATIO_OUTPUT = OutputId("ratio")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("period", ParameterType.INT, default=20, minimum=1),
        ParameterFieldSpec("baseline_period", ParameterType.INT, default=100, minimum=1),
    )
)
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_VALUE_OUTPUT, "float64"),
        OutputFieldSpec(_RATIO_OUTPUT, "float64"),
    )
)


def _validate_periods(period: int, baseline_period: int) -> None:
    if period >= baseline_period:
        raise ComponentValidationError(
            _COMPONENT_ID,
            f"period ({period}) must be less than baseline_period ({baseline_period})",
        )


class RelativeVolatilityComponent:
    """Semantic rolling realized volatility of log returns, plus its ratio to a
    longer baseline window (the "rolling" and "relative" halves of the
    regime-volatility PRD bullet, SPRINT_051.md).

    Log returns follow the one shared definition used across this sprint's
    catalog (D-S051-03): ``r_t = ln(close_t / close_{t-1})``, which loses one
    bar relative to ``close`` (there is no prior close for bar 0).

        value[i]    = population_stdev(r[i-period+1 : i+1])
        baseline[i] = population_stdev(r[i-baseline_period+1 : i+1])
        ratio[i]    = value[i] / baseline[i]

    Both use the same POPULATION standard deviation estimator (``ddof=0``, no
    Bessel's correction), per D-S051-05 -- one documented estimator rather
    than matching any particular library's default.

    Zero-baseline convention -- this component follows the project's ORDINARY
    zero-denominator convention (unlike ``momentum.stochastic``'s deliberate
    D-S051-04 divergence, which does not generalize here: there is no
    analogous "0.0 fabricates a real signal" concern for a volatility
    ratio). When ``baseline == 0.0`` (a perfectly flat baseline window, so
    every log return in it is exactly 0.0), ``ratio`` is defined as ``0.0``
    rather than an incidental ``inf``/``NaN`` from the division -- matching
    ``candle.wick`` (D-S047-10) and ``trend.ema_distance`` /
    ``volatility.range_expansion`` (D-S048-10).

    Warmup: the component's single, shared warmup is ``baseline_period``
    bars of ``close`` -- the wider window that gates ``ratio``'s validity,
    counted in ``close`` bars (not ``returns`` bars) despite returns losing
    one bar, exactly as this task's acceptance criterion states. ``value``'s
    own narrower ``period``-bar window is valid earlier in the underlying
    array (mirroring ``momentum.macd``'s ``line`` output being valid before
    ``signal``), but the component's reported ``valid_from_index`` is the
    shared ``baseline_period``, since that is what the whole component --
    including ``ratio`` -- needs before it is meaningful.
    """

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = _PARAMETER_SCHEMA
    output_schema = _OUTPUT_SCHEMA

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        period = int(parameters.get("period"))
        baseline_period = int(parameters.get("baseline_period"))
        _validate_periods(period, baseline_period)
        return HistoryRequirement(bars_before=baseline_period)

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


class NumpyRelativeVolatilityImplementation:
    """NumPy Relative Volatility backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        period = int(parameters.get("period"))
        baseline_period = int(parameters.get("baseline_period"))
        _validate_periods(period, baseline_period)
        bar_count = len(workspace.market)
        close = np.asarray(workspace.market.close.values, dtype=np.float64)

        returns = log_returns(close)

        value = np.full(bar_count, np.nan, dtype=np.float64)
        baseline = np.full(bar_count, np.nan, dtype=np.float64)
        valid_returns = returns[1:]
        if valid_returns.size > 0:
            value[1:] = rolling_population_stdev(valid_returns, period)
            baseline[1:] = rolling_population_stdev(valid_returns, baseline_period)

        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(baseline == 0.0, 0.0, value / baseline)

        outputs: dict[OutputId, OutputSeries] = {
            _VALUE_OUTPUT: ndarray_to_output_series(value),
            _RATIO_OUTPUT: ndarray_to_output_series(ratio),
        }
        # Derived from the component's own declared history_requirement, not
        # recomputed from `baseline_period` independently -- so a regression
        # in bars_before (the planner's look-back contract) shows up here
        # too, instead of silently diverging from what was actually
        # requested (the RSI lesson, Sprint 051 T003).
        warmup_bars = RelativeVolatilityComponent().history_requirement(parameters).bars_before

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


__all__ = ["NumpyRelativeVolatilityImplementation", "RelativeVolatilityComponent"]
