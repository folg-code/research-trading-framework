"""List published market-data datasets for read-only catalog consumers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

from trading_framework.core.exceptions import TradingFrameworkError
from trading_framework.infrastructure.storage.paths import market_data_root
from trading_framework.market.datasets import DatasetLifecycleState, DatasetMetadata

_METADATA_DIR_NAME: Final = "metadata"
_CORRUPT_METADATA_ERRORS: Final = (OSError, ValueError, KeyError, TypeError, TradingFrameworkError)


@dataclass(frozen=True, slots=True)
class PublishedDatasetSummary:
    """Read-only summary of one PUBLISHED dataset, safe to expose to a local UI.

    Deliberately narrower than ``DatasetMetadata``: no checksum, lineage, or storage
    path, matching the workbench API's "no filesystem path the operator did not
    supply" rule (ADR-0037 §4).
    """

    dataset_ref: str
    instrument_id: str
    timeframe: str
    start_at: datetime
    end_at: datetime
    row_count: int


def list_published_datasets(storage_root: Path) -> tuple[PublishedDatasetSummary, ...]:
    """Scan the metadata store and return every PUBLISHED dataset, sorted by identity.

    Read-only: never mutates a metadata file. A corrupt or unreadable metadata
    entry is skipped rather than raised, since one bad file must not break the
    whole listing for every other dataset.
    """
    metadata_root = market_data_root(storage_root) / _METADATA_DIR_NAME
    if not metadata_root.is_dir():
        return ()

    summaries: list[PublishedDatasetSummary] = []
    for path in sorted(metadata_root.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            metadata = DatasetMetadata.from_dict(payload)
        except _CORRUPT_METADATA_ERRORS:
            continue
        if metadata.lifecycle_status is not DatasetLifecycleState.PUBLISHED:
            continue
        summaries.append(
            PublishedDatasetSummary(
                dataset_ref=str(metadata.dataset_ref),
                instrument_id=metadata.instrument_id.value,
                timeframe=metadata.timeframe.value,
                start_at=metadata.start_at,
                end_at=metadata.end_at,
                row_count=metadata.row_count,
            )
        )
    return tuple(summaries)
