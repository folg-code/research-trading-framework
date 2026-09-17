"""Structure Level Role Reversal Market Analysis component."""

import numpy as np

from trading_framework.market_analysis.adapters.numpy.level_role_reversal import (
    level_role_reversal,
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

_COMPONENT_ID = ComponentId("structure.level_role_reversal")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("numpy.level_role_reversal")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

_SWING_ID = ComponentId("structure.swing")
_LATEST_SWING_HIGH_LEVEL = OutputId("latest_swing_high_level")
_LATEST_SWING_LOW_LEVEL = OutputId("latest_swing_low_level")

_RESISTANCE_TO_SUPPORT_EVENT = OutputId("resistance_to_support_event")
_SUPPORT_TO_RESISTANCE_EVENT = OutputId("support_to_resistance_event")

_PARAMETER_SCHEMA = ParameterSchema(
    fields=(
        ParameterFieldSpec("pivot_range", ParameterType.INT, default=2, minimum=1),
        ParameterFieldSpec("retest_window", ParameterType.INT, default=5, minimum=1),
    )
)
_OUTPUT_SCHEMA = OutputSchema(
    outputs=(
        OutputFieldSpec(_RESISTANCE_TO_SUPPORT_EVENT, "float64"),
        OutputFieldSpec(_SUPPORT_TO_RESISTANCE_EVENT, "float64"),
    )
)


class LevelRoleReversalComponent:
    """Causal level role flip after being broken and retested ("SR flip").

    Using ``structure.swing``'s latest confirmed swing high/low as the
    level: when a bar closes beyond the *prior* bar's latest swing-high
    level (a resistance break), and within ``retest_window`` bars price
    retests that level from above and holds (a bar's low touches back down
    to it while its close stays at or above it),
    ``resistance_to_support_event = 1.0`` fires on the confirming bar --
    the level's role flipped from resistance to support.
    ``support_to_resistance_event`` is the mirror. If the retest instead
    breaks back through the level, or the window elapses with no retest,
    no reversal is confirmed.

    Depends on ``structure.swing`` keyed by ``pivot_range``. No ATR
    dependency: retest/hold is a plain price comparison against the swing
    level, not a normalized distance.
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


class NumpyLevelRoleReversalImplementation:
    """NumPy Level Role Reversal backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        retest_window = int(parameters.get("retest_window"))
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

        arrays = level_role_reversal(
            high,
            low,
            close,
            latest_swing_high_level,
            latest_swing_low_level,
            retest_window=retest_window,
        )

        outputs: dict[OutputId, OutputSeries] = {
            _RESISTANCE_TO_SUPPORT_EVENT: ndarray_to_output_series(
                arrays.resistance_to_support_event
            ),
            _SUPPORT_TO_RESISTANCE_EVENT: ndarray_to_output_series(
                arrays.support_to_resistance_event
            ),
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


__all__ = ["LevelRoleReversalComponent", "NumpyLevelRoleReversalImplementation"]
