"""Historical Parquet datasource contract and implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from dashboard_app.catalog import RunCatalog
from dashboard_app.contracts import ChartWindow
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
