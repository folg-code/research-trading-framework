"""Component and implementation registry."""

from dataclasses import dataclass, field

from trading_framework.core.exceptions import ConfigurationError
from trading_framework.market_analysis.identity.component import ComponentId, ImplementationId
from trading_framework.market_analysis.protocols.batch_component import BatchAnalysisComponent
from trading_framework.market_analysis.protocols.implementation import ComponentImplementation


@dataclass
class _ComponentEntry:
    component: BatchAnalysisComponent
    implementations: dict[str, ComponentImplementation] = field(default_factory=dict)
    default_implementation_id: ImplementationId | None = None


class ComponentRegistry:
    """Registry of semantic components and their backend implementations."""

    def __init__(self) -> None:
        self._entries: dict[str, _ComponentEntry] = {}

    def register(
        self,
        component: BatchAnalysisComponent,
        implementation: ComponentImplementation,
        *,
        default: bool = False,
    ) -> None:
        component_id = component.component_id
        implementation_id = implementation.implementation_id
        entry = self._entries.get(str(component_id))

        if entry is None:
            entry = _ComponentEntry(component=component)
            self._entries[str(component_id)] = entry

        if str(implementation_id) in entry.implementations:
            msg = f"implementation already registered: {implementation_id}"
            raise ConfigurationError(msg)

        entry.implementations[str(implementation_id)] = implementation

        if default:
            if entry.default_implementation_id is not None:
                msg = (
                    f"default implementation already set for {component_id}: "
                    f"{entry.default_implementation_id}"
                )
                raise ConfigurationError(msg)
            entry.default_implementation_id = implementation_id
        elif entry.default_implementation_id is None and len(entry.implementations) == 1:
            entry.default_implementation_id = implementation_id

    def get_component(self, component_id: ComponentId) -> BatchAnalysisComponent:
        entry = self._require_entry(component_id)
        return entry.component

    def resolve(
        self,
        component_id: ComponentId,
        implementation_id: ImplementationId | None = None,
    ) -> tuple[BatchAnalysisComponent, ComponentImplementation]:
        entry = self._require_entry(component_id)
        selected_id = implementation_id or entry.default_implementation_id
        if selected_id is None:
            msg = f"no default implementation registered for {component_id}"
            raise ConfigurationError(msg)

        implementation = entry.implementations.get(str(selected_id))
        if implementation is None:
            msg = f"implementation not registered for {component_id}: {selected_id}"
            raise ConfigurationError(msg)
        return entry.component, implementation

    def _require_entry(self, component_id: ComponentId) -> _ComponentEntry:
        entry = self._entries.get(str(component_id))
        if entry is None:
            msg = f"component not registered: {component_id}"
            raise ConfigurationError(msg)
        return entry
