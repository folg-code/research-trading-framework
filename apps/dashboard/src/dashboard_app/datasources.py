"""Presentation datasource contracts (historical now; AWS dry-run later)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from dashboard_app.catalog import RunCatalog
from dashboard_app.contracts import ChartWindow, RunSummary
from dashboard_app.query import OhlcvWindowResult


@runtime_checkable
class HistoricalRunDataSource(Protocol):
    """Read-only historical research artifacts under a mounted storage root."""

    def list_runs(self) -> RunCatalog:
        """Return the research run catalog."""

    def read_ohlcv_window(
        self,
        *,
        dataset_ref: str,
        window: ChartWindow,
    ) -> OhlcvWindowResult:
        """Return windowed OHLCV for inspection charts."""


@runtime_checkable
class AwsDryRunDataSource(Protocol):
    """Future dry-run datasource contract (Sprint 028: stub only — no HTTP client)."""

    def list_live_sessions(self) -> tuple[RunSummary, ...]:
        """Return dry-run session summaries exposed by a future AWS status API."""

    def fetch_session_snapshot(self, session_id: str) -> dict[str, object]:
        """Return one dry-run session snapshot payload."""


class ParquetHistoricalRunDataSource:
    """Historical datasource backed by ``DashboardQueryService`` + filesystem catalog."""

    def __init__(self, storage_root: Path) -> None:
        from dashboard_app.catalog import list_runs
        from dashboard_app.query import DashboardQueryService

        self._storage_root = storage_root.expanduser().resolve()
        self._query = DashboardQueryService(self._storage_root)
        self._list_runs = list_runs

    def list_runs(self) -> RunCatalog:
        return self._list_runs(self._storage_root)

    def read_ohlcv_window(
        self,
        *,
        dataset_ref: str,
        window: ChartWindow,
    ) -> OhlcvWindowResult:
        return self._query.read_ohlcv_window(dataset_ref=dataset_ref, window=window)


class UnimplementedAwsDryRunDataSource:
    """Placeholder AWS dry-run datasource — raises until a later sprint wires HTTP."""

    def list_live_sessions(self) -> tuple[RunSummary, ...]:
        msg = "AwsDryRunDataSource is not implemented in Sprint 028 (contracts only)"
        raise NotImplementedError(msg)

    def fetch_session_snapshot(self, session_id: str) -> dict[str, object]:
        del session_id
        msg = "AwsDryRunDataSource is not implemented in Sprint 028 (contracts only)"
        raise NotImplementedError(msg)
