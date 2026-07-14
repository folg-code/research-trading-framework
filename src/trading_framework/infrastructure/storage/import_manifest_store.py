"""Persist import manifests for archive-backed datasets."""

import json
from datetime import datetime
from pathlib import Path

from trading_framework.infrastructure.storage.paths import dataset_import_manifest_path
from trading_framework.market.datasets import DatasetRef
from trading_framework.market.importers import ArchiveSourceFormat, ImportManifest
from trading_framework.time.models.utc_instant import require_utc_aware


def write_import_manifest(
    root: Path,
    dataset_ref: DatasetRef,
    manifest: ImportManifest,
) -> Path:
    """Persist ``import_manifest.json`` for a dataset version."""
    path = dataset_import_manifest_path(root, dataset_ref)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest.to_dict(), indent=2),
        encoding="utf-8",
    )
    return path


def read_import_manifest(root: Path, dataset_ref: DatasetRef) -> ImportManifest:
    """Load a persisted import manifest for a dataset version."""
    path = dataset_import_manifest_path(root, dataset_ref)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ImportManifest(
        manifest_version=str(payload["manifest_version"]),
        source_path=str(payload["source_path"]),
        source_format=ArchiveSourceFormat(str(payload["source_format"])),
        source_checksum_sha256=str(payload["source_checksum_sha256"]),
        vendor_schema=str(payload["vendor_schema"]),
        symbol_mapping={str(k): str(v) for k, v in payload["symbol_mapping"].items()},
        decode_row_count=int(payload["decode_row_count"]),
        rejected_row_count=int(payload["rejected_row_count"]),
        imported_at_utc=require_utc_aware(datetime.fromisoformat(str(payload["imported_at_utc"]))),
        normalization_version=str(payload["normalization_version"]),
        framework_version=(
            None if payload.get("framework_version") is None else str(payload["framework_version"])
        ),
    )
