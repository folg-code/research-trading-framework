"""Read-only ``GET /api/v1/datasets`` endpoint body (Sprint 064 T004).

Transport-independent by design (mirrors
``trading_framework.application.execution.vps_status_api``): returns a plain
JSON-serializable payload built only from ``PublishedDatasetSummary``, which
never carries a filesystem path -- matching ADR-0037 section 4's rule that the
API returns no path to the browser for an artifact it did not itself create.
"""

from __future__ import annotations

from typing import Any

from trading_framework.application.market_data import (
    PublishedDatasetSummary,
    list_published_datasets,
)

from workbench_core.api_version import WORKBENCH_API_VERSION
from workbench_core.config import WorkbenchApiConfig


def build_datasets_response(config: WorkbenchApiConfig) -> dict[str, Any]:
    """Build the ``GET /api/v1/datasets`` response body: every PUBLISHED dataset."""
    summaries = list_published_datasets(config.storage_root)
    return {
        "schema_version": WORKBENCH_API_VERSION,
        "datasets": [_summary_to_json(summary) for summary in summaries],
    }


def _summary_to_json(summary: PublishedDatasetSummary) -> dict[str, Any]:
    return {
        "dataset_ref": summary.dataset_ref,
        "instrument_id": summary.instrument_id,
        "timeframe": summary.timeframe,
        "start_at": summary.start_at.isoformat(),
        "end_at": summary.end_at.isoformat(),
        "row_count": summary.row_count,
    }
