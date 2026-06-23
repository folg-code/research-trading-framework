"""Dependency expansion and execution planning."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.errors import CyclicDependencyError
from trading_framework.market_analysis.identity.component import ComponentId, ImplementationId
from trading_framework.market_analysis.identity.computation import ComputationIdentity
from trading_framework.market_analysis.models.dependencies import ComponentDependency
from trading_framework.market_analysis.models.request import ComponentRequest
from trading_framework.market_analysis.planning.context import PlanningContext
from trading_framework.market_analysis.planning.plan import ExecutionPlan, PlannedNode
from trading_framework.market_analysis.registry.registry import ComponentRegistry


def request_key(component_id: ComponentId, parameters_fingerprint: str) -> str:
    return f"{component_id}:{parameters_fingerprint}"


@dataclass(frozen=True, slots=True)
class PlanningRequest:
    """Planner input with optional explicit implementation selection."""

    component_id: ComponentId
    request: ComponentRequest
    implementation_id: ImplementationId | None = None

    @classmethod
    def from_component_request(
        cls,
        request: ComponentRequest,
        *,
        implementation_id: ImplementationId | None = None,
    ) -> "PlanningRequest":
        return cls(
            component_id=request.component_id,
            request=request,
            implementation_id=implementation_id,
        )


class DependencyPlanner:
    """Builds deterministic execution plans from component requests."""

    def __init__(self, registry: ComponentRegistry) -> None:
        self._registry = registry

    def build_plan(
        self,
        context: PlanningContext,
        requests: Sequence[PlanningRequest],
    ) -> ExecutionPlan:
        normalized = self._normalize_requests(requests)
        graph = self._expand_dependencies(normalized)
        ordered_keys = self._topological_sort(graph)
        nodes = self._build_nodes(context, graph, ordered_keys)
        return ExecutionPlan(nodes=nodes)

    def _normalize_requests(
        self,
        requests: Sequence[PlanningRequest],
    ) -> dict[str, PlanningRequest]:
        normalized: dict[str, PlanningRequest] = {}
        for planning_request in requests:
            component = self._registry.get_component(planning_request.component_id)
            canonical = ComponentRequest(
                component_id=planning_request.component_id,
                parameters=component.parameter_schema.canonicalize(
                    planning_request.request.parameters.to_json_dict()
                ),
            )
            key = request_key(canonical.component_id, canonical.parameters.fingerprint())
            if key in normalized:
                existing = normalized[key]
                if (
                    existing.implementation_id is not None
                    and planning_request.implementation_id is not None
                    and existing.implementation_id != planning_request.implementation_id
                ):
                    msg = f"conflicting implementation selection for {canonical.component_id}"
                    raise ValidationError(msg)
                if existing.implementation_id is None:
                    normalized[key] = PlanningRequest(
                        component_id=canonical.component_id,
                        request=canonical,
                        implementation_id=planning_request.implementation_id,
                    )
                continue
            normalized[key] = PlanningRequest(
                component_id=canonical.component_id,
                request=canonical,
                implementation_id=planning_request.implementation_id,
            )
        return normalized

    def _expand_dependencies(
        self,
        seeds: Mapping[str, PlanningRequest],
    ) -> dict[str, tuple[PlanningRequest, tuple[str, ...]]]:
        graph: dict[str, tuple[PlanningRequest, tuple[str, ...]]] = {}
        pending = list(seeds.values())

        while pending:
            planning_request = pending.pop()
            request = planning_request.request
            key = request_key(request.component_id, request.parameters.fingerprint())
            if key in graph:
                continue

            component = self._registry.get_component(request.component_id)
            dependency_keys: list[str] = []
            for dependency in component.component_dependencies(request.parameters):
                dependency_key = self._dependency_request_key(dependency)
                dependency_keys.append(dependency_key)
                if dependency_key not in graph:
                    child_request = ComponentRequest(
                        component_id=dependency.output_ref.component_id,
                        parameters=dependency.output_ref.parameters,
                    )
                    pending.append(PlanningRequest.from_component_request(child_request))

            graph[key] = (planning_request, tuple(sorted(dependency_keys)))
        return graph

    def _dependency_request_key(self, dependency: ComponentDependency) -> str:
        output_ref = dependency.output_ref
        return request_key(output_ref.component_id, output_ref.parameters.fingerprint())

    def _topological_sort(
        self,
        graph: Mapping[str, tuple[PlanningRequest, tuple[str, ...]]],
    ) -> tuple[str, ...]:
        indegree = {key: 0 for key in graph}
        adjacency: dict[str, list[str]] = {key: [] for key in graph}

        for key, (_, dependency_keys) in graph.items():
            for dependency_key in dependency_keys:
                if dependency_key not in graph:
                    msg = f"missing dependency node: {dependency_key}"
                    raise ValidationError(msg)
                indegree[key] += 1
                adjacency[dependency_key].append(key)

        ready = sorted(key for key, degree in indegree.items() if degree == 0)
        ordered: list[str] = []

        while ready:
            current = ready.pop(0)
            ordered.append(current)
            for dependent in sorted(adjacency[current]):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    ready.append(dependent)
            ready.sort()

        if len(ordered) != len(graph):
            cycle = self._find_cycle(graph)
            raise CyclicDependencyError(cycle)

        return tuple(ordered)

    def _find_cycle(
        self,
        graph: Mapping[str, tuple[PlanningRequest, tuple[str, ...]]],
    ) -> tuple[str, ...]:
        visited: set[str] = set()
        stack: set[str] = set()
        path: list[str] = []

        def visit(node: str) -> tuple[str, ...] | None:
            visited.add(node)
            stack.add(node)
            path.append(node)
            _, dependency_keys = graph[node]
            for dependency_key in dependency_keys:
                if dependency_key not in visited:
                    found = visit(dependency_key)
                    if found is not None:
                        return found
                elif dependency_key in stack:
                    cycle_start = path.index(dependency_key)
                    return (*path[cycle_start:], dependency_key)
            path.pop()
            stack.remove(node)
            return None

        for node in sorted(graph):
            if node not in visited:
                found = visit(node)
                if found is not None:
                    return found
        return tuple(sorted(graph)[:1])

    def _build_nodes(
        self,
        context: PlanningContext,
        graph: Mapping[str, tuple[PlanningRequest, tuple[str, ...]]],
        ordered_keys: Sequence[str],
    ) -> tuple[PlannedNode, ...]:
        computation_keys: dict[str, str] = {}
        nodes: list[PlannedNode] = []

        for key in ordered_keys:
            planning_request, dependency_request_keys = graph[key]
            dependency_keys = tuple(
                sorted(
                    computation_keys[dependency_key] for dependency_key in dependency_request_keys
                )
            )
            component, implementation = self._registry.resolve(
                planning_request.component_id,
                planning_request.implementation_id,
            )
            identity = ComputationIdentity(
                component_id=component.component_id,
                component_version=component.component_version,
                implementation_id=implementation.implementation_id,
                implementation_version=implementation.implementation_version,
                parameters=planning_request.request.parameters,
                dataset_ref=context.dataset_ref,
                timeframe=context.timeframe,
                requested_range=context.requested_range,
                dependency_keys=dependency_keys,
            )
            identity_key = identity.canonical_key()
            computation_keys[key] = identity_key
            if any(node.computation_identity.canonical_key() == identity_key for node in nodes):
                continue

            nodes.append(
                PlannedNode(
                    request=planning_request.request,
                    component=component,
                    implementation=implementation,
                    computation_identity=identity,
                    dependency_keys=dependency_keys,
                )
            )
        return tuple(nodes)
