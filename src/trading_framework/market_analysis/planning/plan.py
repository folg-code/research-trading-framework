"""Execution plan models."""

from dataclasses import dataclass

from trading_framework.market_analysis.identity.computation import ComputationIdentity
from trading_framework.market_analysis.models.request import ComponentRequest
from trading_framework.market_analysis.protocols.batch_component import BatchAnalysisComponent
from trading_framework.market_analysis.protocols.implementation import ComponentImplementation


@dataclass(frozen=True, slots=True)
class PlannedNode:
    """One resolved computation in deterministic execution order."""

    request: ComponentRequest
    component: BatchAnalysisComponent
    implementation: ComponentImplementation
    computation_identity: ComputationIdentity
    dependency_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Deterministic batch execution plan with deduplicated nodes."""

    nodes: tuple[PlannedNode, ...]

    def computation_keys(self) -> tuple[str, ...]:
        return tuple(node.computation_identity.canonical_key() for node in self.nodes)
