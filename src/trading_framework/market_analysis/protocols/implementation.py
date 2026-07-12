"""Component implementation protocol."""

from typing import Protocol

from trading_framework.market_analysis.identity.component import (
    ImplementationId,
    ImplementationVersion,
)
from trading_framework.market_analysis.models.context import AnalysisContext
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView


class ComponentImplementation(Protocol):
    """Backend implementation of one semantic component."""

    @property
    def implementation_id(self) -> ImplementationId: ...

    @property
    def implementation_version(self) -> ImplementationVersion: ...

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult: ...
