"""Discover persisted dataset metadata by logical identity."""

from __future__ import annotations

import json
import re
from pathlib import Path

from trading_framework.infrastructure.storage.paths import dataset_metadata_path
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
)

_LEGACY_VERSION_FILENAME = re.compile(r"^v(\d+)$")
_NEW_LAYOUT_VERSION_SUFFIX = re.compile(r"\.v(\d+)$")


def list_dataset_refs(
    storage_root: Path,
    dataset_id: DatasetId,
) -> tuple[DatasetRef, ...]:
    """Return dataset versions found for one logical identity, sorted by version.

    ``dataset_id.asset_class`` selects which physical layout to scan (new,
    filename-encodes-version vs. legacy, one ``v{n}.json`` file per version)
    -- callers pass the same identity shape they would use to resolve any
    other path for this dataset (ADR: market-data directory layout
    simplification).
    """
    metadata_dir = dataset_metadata_path(
        storage_root,
        DatasetRef(dataset_id=dataset_id, version=1),
    ).parent
    if not metadata_dir.exists():
        return ()

    refs: list[DatasetRef] = []
    if dataset_id.asset_class is not None:
        prefix = f"{dataset_id.data_type}.{dataset_id.source_id}."
        for path in metadata_dir.glob(f"{prefix}v*.json"):
            match = _NEW_LAYOUT_VERSION_SUFFIX.search(path.stem)
            if match is None:
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            refs.append(DatasetMetadata.from_dict(payload).dataset_ref)
    else:
        for path in metadata_dir.glob("v*.json"):
            if _LEGACY_VERSION_FILENAME.match(path.stem) is None:
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            refs.append(DatasetMetadata.from_dict(payload).dataset_ref)
    return tuple(sorted(refs, key=lambda ref: ref.version))


def latest_dataset_ref(
    storage_root: Path,
    dataset_id: DatasetId,
) -> DatasetRef | None:
    """Return the highest-version dataset ref for one identity when present."""
    refs = list_dataset_refs(storage_root, dataset_id)
    if not refs:
        return None
    return refs[-1]


def latest_published_dataset_ref(
    storage_root: Path,
    dataset_id: DatasetId,
) -> DatasetRef | None:
    """Return the highest-version published dataset ref for one identity."""
    refs = list_dataset_refs(storage_root, dataset_id)
    for dataset_ref in reversed(refs):
        metadata_path = dataset_metadata_path(storage_root, dataset_ref)
        metadata = DatasetMetadata.from_dict(
            json.loads(metadata_path.read_text(encoding="utf-8")),
        )
        if metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED:
            return dataset_ref
    return None
