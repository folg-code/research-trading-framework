"""Component implementation protocol."""

from collections.abc import Mapping
from typing import Protocol

from trading_framework.market_analysis.identity.component import (
    ImplementationId,
    ImplementationVersion,
)
from trading_framework.market_analysis.models.context import AnalysisContext
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.market_analysis.models.result import AnalysisResult


class ComponentImplementation(Protocol):
    """Backend implementation of one semantic component."""

    @property
    def implementation_id(self) -> ImplementationId: ...

    @property
    def implementation_version(self) -> ImplementationVersion: ...

    def compute(
        self,
        context: AnalysisContext,
        parameters: CanonicalParameters,
        dependency_results: Mapping[str, AnalysisResult],
    ) -> AnalysisResult: ...
