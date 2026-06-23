"""Batch analysis component protocol."""

from typing import Protocol

from trading_framework.market_analysis.identity.component import ComponentId, ComponentVersion
from trading_framework.market_analysis.models.dependencies import (
    ComponentDependency,
    DataFieldDependency,
)
from trading_framework.market_analysis.models.history import HistoryRequirement
from trading_framework.market_analysis.models.kind import Causality, ComponentKind
from trading_framework.market_analysis.models.outputs import OutputSchema
from trading_framework.market_analysis.models.parameters import CanonicalParameters, ParameterSchema


class BatchAnalysisComponent(Protocol):
    """Semantic Market Analysis component contract."""

    @property
    def component_id(self) -> ComponentId: ...

    @property
    def component_version(self) -> ComponentVersion: ...

    @property
    def kind(self) -> ComponentKind: ...

    @property
    def causality(self) -> Causality: ...

    @property
    def parameter_schema(self) -> ParameterSchema: ...

    @property
    def output_schema(self) -> OutputSchema: ...

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement: ...

    def data_dependencies(
        self, parameters: CanonicalParameters
    ) -> tuple[DataFieldDependency, ...]: ...

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]: ...
