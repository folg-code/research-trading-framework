"""Dataset metadata persistence."""

import json
from pathlib import Path

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import dataset_metadata_path
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    DatasetVersionAllocator,
    InMemoryDatasetVersionAllocator,
)


class FileDatasetRegistry:
    """Persist dataset metadata to a local metadata store."""

    def __init__(
        self,
        root: Path,
        allocator: DatasetVersionAllocator | None = None,
    ) -> None:
        self._root = root
        self._allocator = allocator or InMemoryDatasetVersionAllocator()

    def allocate_ref(self, dataset_id: DatasetId) -> DatasetRef:
        """Allocate the next dataset version for ``dataset_id``."""
        return DatasetRef(
            dataset_id=dataset_id,
            version=self._allocator.allocate_next(dataset_id),
        )

    def register(self, metadata: DatasetMetadata) -> None:
        """Persist a WORKING dataset version."""
        if metadata.lifecycle_status is not DatasetLifecycleState.WORKING:
            msg = "registry only accepts WORKING dataset versions"
            raise ValidationError(msg)

        path = dataset_metadata_path(self._root, metadata.dataset_ref)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(metadata.to_dict(), indent=2),
            encoding="utf-8",
        )

    def get(self, dataset_ref: DatasetRef) -> DatasetMetadata:
        """Load metadata for a dataset version."""
        path = dataset_metadata_path(self._root, dataset_ref)
        if not path.exists():
            msg = f"dataset metadata not found: {dataset_ref}"
            raise ValidationError(msg)
        payload = json.loads(path.read_text(encoding="utf-8"))
        return DatasetMetadata.from_dict(payload)
