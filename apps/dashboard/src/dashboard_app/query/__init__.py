"""DuckDB-backed read queries over mounted Parquet artifacts."""

from dashboard_app.query.dataset_locator import DatasetLocator
from dashboard_app.query.service import (
    DEFAULT_MAX_BARS,
    DEFAULT_MAX_PARQUET_ROWS,
    DashboardQueryService,
    OhlcvBarRow,
    OhlcvWindowResult,
)

__all__ = [
    "DEFAULT_MAX_BARS",
    "DEFAULT_MAX_PARQUET_ROWS",
    "DashboardQueryService",
    "DatasetLocator",
    "OhlcvBarRow",
    "OhlcvWindowResult",
]
