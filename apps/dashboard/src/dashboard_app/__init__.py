"""Trading research dashboard application package."""

from dashboard_app.catalog import RunCatalog, list_runs
from dashboard_app.config import DEFAULT_LIVE_PAPER_STATUS_URL, DashboardSettings, load_settings
from dashboard_app.contracts import (
    PRESENTATION_SCHEMA_VERSION,
    ChartWindow,
    RunManifest,
    RunSummary,
    TradeView,
    WorkflowKind,
)
from dashboard_app.query import DashboardQueryService, OhlcvBarRow, OhlcvWindowResult

__all__ = [
    "DEFAULT_LIVE_PAPER_STATUS_URL",
    "PRESENTATION_SCHEMA_VERSION",
    "ChartWindow",
    "DashboardQueryService",
    "DashboardSettings",
    "OhlcvBarRow",
    "OhlcvWindowResult",
    "RunCatalog",
    "RunManifest",
    "RunSummary",
    "TradeView",
    "WorkflowKind",
    "list_runs",
    "load_settings",
]
