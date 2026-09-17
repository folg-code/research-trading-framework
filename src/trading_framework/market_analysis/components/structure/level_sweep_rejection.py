"""Structure Level Sweep Rejection Market Analysis component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.level_sweep_rejection import (
    level_sweep_rejection,
)
from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.components.structure.swing import SwingStructureComponent
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

_COMPONENT_ID = ComponentId("structure.level_sweep_rejection")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.level_sweep_rejection")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_SWING_ID = ComponentId("structure.swing")
_LATEST_SWING_HIGH_LEVEL = OutputId("latest_swing_high_level")
_LATEST_SWING_LOW_LEVEL = OutputId("latest_swing_low_level")

_HIGH_REJECTION_EVENT = OutputId("high_rejection_event")
_LOW_REJECTION_EVENT = OutputId("low_rejection_event")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("pivot_range", ParameterType.INT, default=2, minimum=1),
        ParameterFieldSpec("observation_window", ParameterType.INT, default=5, minimum=1),
    )
)
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_HIGH_REJECTION_EVENT, "float64"),
        OutputFieldSpec(_LOW_REJECTION_EVENT, "float64"),
    )
)


class LevelSweepRejectionComponent:
    """Causal level pierced then rejected back within a window ("liquidity grab").

    Using ``structure.swing``'s latest confirmed swing high/low as the
    level: when a bar's high pierces the *prior* bar's latest swing-high
    level, and within ``observation_window`` bars (including the pierce
    bar itself) a bar's close falls back below that level,
    ``high_rejection_event = 1.0`` fires on the closing (rejecting) bar.
    ``low_rejection_event`` is the mirror (low pierces the swing-low level,
    a later close reclaims above it). If the window elapses with no
    rejecting close, the sweep is not flagged -- the level was genuinely
    taken out, not rejected.

    Depends on ``structure.swing`` keyed by ``pivot_range``. No ATR
    dependency: the pierce/rejection test is a plain price comparison
    against the swing level itself, not a normalized distance.
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
        return (
            DataFieldDependency("high"),
            DataFieldDependency("low"),
            DataFieldDependency("close"),
        )

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        pivot_range = int(parameters.get("pivot_range"))
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=_SWING_ID,
                    parameters=SwingStructureComponent().parameter_schema.canonicalize(
                        {"pivot_range": pivot_range}
                    ),
                    output_id=_LATEST_SWING_HIGH_LEVEL,
                )
            ),
        )


class NumpyLevelSweepRejectionImplementation:
    """NumPy Level Sweep Rejection backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        observation_window = int(parameters.get("observation_window"))
        bar_count = len(workspace.market)
        high = np.asarray(workspace.market.high.values, dtype=np.float64)
        low = np.asarray(workspace.market.low.values, dtype=np.float64)
        close = np.asarray(workspace.market.close.values, dtype=np.float64)

        # Only one component_dependencies() entry is declared (structure.swing),
        # so its single AnalysisResult carries both level outputs we need.
        swing_result = next(iter(workspace.dependency_results.values()))
        latest_swing_high_level = np.asarray(
            swing_result.outputs[_LATEST_SWING_HIGH_LEVEL].values, dtype=np.float64
        )
        latest_swing_low_level = np.asarray(
            swing_result.outputs[_LATEST_SWING_LOW_LEVEL].values, dtype=np.float64
        )

        arrays = level_sweep_rejection(
            high,
            low,
            close,
            latest_swing_high_level,
            latest_swing_low_level,
            observation_window=observation_window,
        )

        outputs: dict[OutputId, OutputSeries] = {
            _HIGH_REJECTION_EVENT: ndarray_to_output_series(arrays.high_rejection_event),
            _LOW_REJECTION_EVENT: ndarray_to_output_series(arrays.low_rejection_event),
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
            warmup_bars=0,
            valid_from_index=0,
            bar_count=bar_count,
            workspace=workspace,
        )


__all__ = ["LevelSweepRejectionComponent", "NumpyLevelSweepRejectionImplementation"]
