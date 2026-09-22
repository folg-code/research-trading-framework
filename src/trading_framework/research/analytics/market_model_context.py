"""Generic Market Model categorical-context resolution.

Extracted from ``context_expectancy.py`` (Sprint 073 / Phase 18 18B
Milestone 1) so Signal Research's ``context_timeline``/
``context_persistence`` can reuse the exact same mechanism 18A's
``context_expectancy`` already built and verified, instead of a second
copy. Not specific to any one workflow: any caller with a
``MarketModelDefinition`` and an assembled ``AnalysisFrame`` can use this.

The persisted Market Model result (``market_model_result_dataframe``) is a
single boolean gate column only; every intermediate component value is
discarded there. Callers must instead assemble an ``AnalysisFrame`` (built
the same way ``evaluate_models`` already builds one -- either already in
memory for a live run, or recomputed post-hoc via ``run_analysis``) and use
this module to select only the columns whose owning component is
``ComponentKind.STATE`` and is actually referenced by the Market Model's
own expression. Continuous (``FEATURE``) or structural (``STRUCTURE``)
components are never treated as context, even though every component's
declared dtype is the same ``float64`` regardless of kind.
"""

from __future__ import annotations

from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.market_analysis.models.kind import ComponentKind
from trading_framework.market_analysis.registry.builtins import default_mvp_registry
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.model_expression.planning import collect_model_dependencies


def state_context_aliases(
    *,
    market_model: MarketModelDefinition,
    frame: AnalysisFrame,
    registry: ComponentRegistry | None = None,
) -> dict[str, str]:
    """Map a frame column alias to its owning component id, STATE-kind only.

    Only components the Market Model's own expression references qualify --
    a signal-model-only dependency that happens to share the frame is never
    treated as market context.
    """
    registry = registry or default_mvp_registry()
    dependencies = collect_model_dependencies(market_models=(market_model,), signal_models=())
    market_component_ids = {ref.component_id for ref in dependencies.component_output_references}

    aliases: dict[str, str] = {}
    for alias, output_ref in frame.column_lineage.items():
        component_id = output_ref.computation_identity.component_id
        if component_id not in market_component_ids:
            continue
        if registry.get_component(component_id).kind is not ComponentKind.STATE:
            continue
        aliases[alias] = str(component_id)
    return aliases
