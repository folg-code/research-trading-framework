"""Execution plan models."""

from dataclasses import dataclass

from trading_framework.market_analysis.identity.computation import ComputationIdentity
from trading_framework.market_analysis.identity.mtf import ResampleIdentity
from trading_framework.market_analysis.models.request import ComponentRequest
from trading_framework.market_analysis.models.resample import ResampleSpec
from trading_framework.market_analysis.protocols.batch_component import BatchAnalysisComponent
from trading_framework.market_analysis.protocols.implementation import ComponentImplementation


@dataclass(frozen=True, slots=True)
class ResampleNode:
    """Shared resampling stage in the execution DAG — not a registry component."""

    resample_identity: ResampleIdentity
    resample_spec: ResampleSpec
    source_input_key: str | None = None


@dataclass(frozen=True, slots=True)
class PlannedNode:
    """One resolved computation in deterministic execution order."""

    request: ComponentRequest
    component: BatchAnalysisComponent
    implementation: ComponentImplementation
    computation_identity: ComputationIdentity
    dependency_keys: tuple[str, ...]


ExecutionNode = ResampleNode | PlannedNode


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Deterministic batch execution plan with deduplicated nodes."""

    nodes: tuple[ExecutionNode, ...]

    def component_nodes(self) -> tuple[PlannedNode, ...]:
        return tuple(node for node in self.nodes if isinstance(node, PlannedNode))

    def resample_nodes(self) -> tuple[ResampleNode, ...]:
        return tuple(node for node in self.nodes if isinstance(node, ResampleNode))

    def computation_keys(self) -> tuple[str, ...]:
        return tuple(node.computation_identity.canonical_key() for node in self.component_nodes())

    def resample_keys(self) -> tuple[str, ...]:
        return tuple(node.resample_identity.canonical_key() for node in self.resample_nodes())
