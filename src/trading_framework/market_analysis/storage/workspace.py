"""Execution-scoped analysis workspace."""

from dataclasses import dataclass

from trading_framework.market_analysis.assembly.session_metadata import TradingSessionMetadata
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.identity.computation import ComputationIdentity
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.storage.result_store import AnalysisResultStore
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions.protocol import TradingSessionResolver


@dataclass(frozen=True, slots=True)
class AnalysisWorkspaceView:
    """Read-only execution view passed to component implementations."""

    market: AnalysisDataView
    dependency_results: dict[str, AnalysisResult]
    computation_timeframe: Timeframe | None = None
    input_identity_key: str | None = None
    planned_computation_identity: ComputationIdentity | None = None
    session_metadata: TradingSessionMetadata | None = None


class AnalysisWorkspace:
    """Executor-controlled workspace for one execution plan."""

    def __init__(
        self,
        market_view: AnalysisDataView,
        *,
        session_metadata: TradingSessionMetadata | None = None,
        session_resolver: TradingSessionResolver | None = None,
    ) -> None:
        self._market_view = market_view
        self._session_metadata = session_metadata
        self._session_resolver = session_resolver
        self._resampled_views: dict[str, AnalysisDataView] = {}
        self._resampled_session_metadata: dict[str, TradingSessionMetadata] = {}
        self._store = AnalysisResultStore()

    @property
    def market_view(self) -> AnalysisDataView:
        return self._market_view

    @property
    def session_metadata(self) -> TradingSessionMetadata | None:
        return self._session_metadata

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
        computation_timeframe: Timeframe | None = None,
        planned_computation_identity: ComputationIdentity | None = None,
    ) -> AnalysisWorkspaceView:
        market = self.market_view_for(input_identity_key)
        return AnalysisWorkspaceView(
            market=market,
            dependency_results=self._store.dependency_results(dependency_keys),
            computation_timeframe=computation_timeframe,
            input_identity_key=input_identity_key,
            planned_computation_identity=planned_computation_identity,
            session_metadata=self._session_metadata_for(market, input_identity_key),
        )

    def _session_metadata_for(
        self,
        market: AnalysisDataView,
        input_identity_key: str | None,
    ) -> TradingSessionMetadata | None:
        if input_identity_key is None:
            if self._session_metadata is not None and len(self._session_metadata) == len(market):
                return self._session_metadata
            return None
        cached = self._resampled_session_metadata.get(input_identity_key)
        if cached is not None:
            return cached
        if self._session_resolver is None:
            return None
        resolved = TradingSessionMetadata.resolve(market.timestamps, self._session_resolver)
        self._resampled_session_metadata[input_identity_key] = resolved
        return resolved
