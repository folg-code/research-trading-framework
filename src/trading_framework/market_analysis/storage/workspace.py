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
        self._resampled_views: dict[str, AnalysisDataView] = {}
        self._store = AnalysisResultStore()

    @property
    def market_view(self) -> AnalysisDataView:
        return self._market_view

    @property
    def result_store(self) -> AnalysisResultStore:
        return self._store

    def register(self, result: AnalysisResult) -> None:
        self._store.put(result)

    def register_resampled_view(self, identity_key: str, view: AnalysisDataView) -> None:
        self._resampled_views[identity_key] = view

    def market_view_for(self, input_identity_key: str | None) -> AnalysisDataView:
        if input_identity_key is None:
            return self._market_view
        return self._resampled_views[input_identity_key]

    def view_for(
        self,
        dependency_keys: tuple[str, ...],
        *,
        input_identity_key: str | None = None,
    ) -> AnalysisWorkspaceView:
        return AnalysisWorkspaceView(
            market=self.market_view_for(input_identity_key),
            dependency_results=self._store.dependency_results(dependency_keys),
        )
