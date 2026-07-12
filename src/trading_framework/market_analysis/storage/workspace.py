"""Execution-scoped analysis workspace."""

from dataclasses import dataclass

from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.storage.result_store import AnalysisResultStore


@dataclass(frozen=True, slots=True)
class AnalysisWorkspaceView:
    """Read-only execution view passed to component implementations."""

    market: AnalysisDataView
    dependency_results: dict[str, AnalysisResult]


class AnalysisWorkspace:
    """Executor-controlled workspace for one execution plan."""

    def __init__(self, market_view: AnalysisDataView) -> None:
        self._market_view = market_view
        self._store = AnalysisResultStore()

    @property
    def market_view(self) -> AnalysisDataView:
        return self._market_view

    @property
    def result_store(self) -> AnalysisResultStore:
        return self._store

    def register(self, result: AnalysisResult) -> None:
        self._store.put(result)

    def view_for(self, dependency_keys: tuple[str, ...]) -> AnalysisWorkspaceView:
        return AnalysisWorkspaceView(
            market=self._market_view,
            dependency_results=self._store.dependency_results(dependency_keys),
        )
