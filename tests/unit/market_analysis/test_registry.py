"""Component registry tests."""

import pytest

from trading_framework.core.exceptions import ConfigurationError
from trading_framework.market_analysis import (
    AnalysisContext,
    AnalysisResult,
    CanonicalParameters,
    Causality,
    ComponentDependency,
    ComponentId,
    ComponentKind,
    ComponentVersion,
    DataFieldDependency,
    HistoryRequirement,
    ImplementationId,
    ImplementationVersion,
    OutputFieldSpec,
    OutputId,
    OutputSchema,
    ParameterSchema,
)
from trading_framework.market_analysis.registry import ComponentRegistry
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView


class _CloseComponent:
    component_id = ComponentId("price.close")
    component_version = ComponentVersion("1.0.0")
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = ParameterSchema(fields=())
    output_schema = OutputSchema(outputs=(OutputFieldSpec(OutputId("value"), "float64"),))

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        return HistoryRequirement(bars_before=0)

    def data_dependencies(self, parameters: CanonicalParameters) -> tuple[DataFieldDependency, ...]:
        return (DataFieldDependency("close"),)

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        return ()


class _CloseNumpy:
    implementation_id = ImplementationId("numpy.close")
    implementation_version = ImplementationVersion("1.0.0")

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        raise NotImplementedError


class _ClosePandas:
    implementation_id = ImplementationId("pandas.close")
    implementation_version = ImplementationVersion("1.0.0")

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        raise NotImplementedError


def test_register_and_resolve_default_implementation() -> None:
    registry = ComponentRegistry()
    component = _CloseComponent()
    implementation = _CloseNumpy()
    registry.register(component, implementation)

    resolved_component, resolved_implementation = registry.resolve(ComponentId("price.close"))
    assert resolved_component is component
    assert resolved_implementation is implementation


def test_first_implementation_becomes_implicit_default() -> None:
    registry = ComponentRegistry()
    registry.register(_CloseComponent(), _CloseNumpy())
    _, resolved = registry.resolve(ComponentId("price.close"))
    assert resolved.implementation_id == ImplementationId("numpy.close")


def test_explicit_implementation_selection() -> None:
    registry = ComponentRegistry()
    registry.register(_CloseComponent(), _CloseNumpy())
    registry.register(_CloseComponent(), _ClosePandas())
    _, resolved = registry.resolve(
        ComponentId("price.close"),
        ImplementationId("pandas.close"),
    )
    assert resolved.implementation_id == ImplementationId("pandas.close")


def test_duplicate_default_raises_configuration_error() -> None:
    registry = ComponentRegistry()
    registry.register(_CloseComponent(), _CloseNumpy(), default=True)
    with pytest.raises(ConfigurationError, match="default implementation already set"):
        registry.register(_CloseComponent(), _ClosePandas(), default=True)


def test_duplicate_implementation_raises_configuration_error() -> None:
    registry = ComponentRegistry()
    registry.register(_CloseComponent(), _CloseNumpy())
    with pytest.raises(ConfigurationError, match="implementation already registered"):
        registry.register(_CloseComponent(), _CloseNumpy())


def test_unknown_component_raises_configuration_error() -> None:
    registry = ComponentRegistry()
    with pytest.raises(ConfigurationError, match="component not registered"):
        registry.resolve(ComponentId("price.close"))
