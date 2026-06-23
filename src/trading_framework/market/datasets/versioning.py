"""Dataset version allocation and material-change policy."""

from enum import StrEnum
from typing import Protocol

from trading_framework.market.datasets.identity import DatasetId


class MaterialChangeReason(StrEnum):
    """Reasons that require a new dataset version in the MVP algorithm."""

    SOURCE_DATA_CHANGED = "source_data_changed"
    RECORDS_CORRECTED = "records_corrected"
    NORMALIZATION_CHANGED = "normalization_changed"
    SCHEMA_CHANGED = "schema_changed"
    VALIDATION_OUTCOME_CHANGED = "validation_outcome_changed"


class DatasetVersionPolicy:
    """Determine whether a material change requires a new dataset version."""

    @staticmethod
    def requires_new_version(
        *,
        material_change: MaterialChangeReason | None,
        content_checksum_changed: bool,
    ) -> bool:
        """Return whether a new version must be allocated."""
        if material_change is not None:
            return True
        return content_checksum_changed


class DatasetVersionAllocator(Protocol):
    """Allocate monotonically increasing versions per dataset identity."""

    def latest_version(self, dataset_id: DatasetId) -> int | None:
        """Return the latest allocated version, if any."""
        ...

    def allocate_next(self, dataset_id: DatasetId) -> int:
        """Allocate and return the next version for the dataset identity."""
        ...


class InMemoryDatasetVersionAllocator:
    """In-memory version allocator for tests and early workflows."""

    def __init__(self) -> None:
        self._versions: dict[str, int] = {}

    def latest_version(self, dataset_id: DatasetId) -> int | None:
        version = self._versions.get(dataset_id.canonical())
        return None if version is None else version

    def allocate_next(self, dataset_id: DatasetId) -> int:
        key = dataset_id.canonical()
        next_version = self._versions.get(key, 0) + 1
        self._versions[key] = next_version
        return next_version

    def reuse_current(self, dataset_id: DatasetId) -> int:
        """Return the current version without allocation, for non-material rewrites."""
        latest = self.latest_version(dataset_id)
        if latest is None:
            msg = "cannot reuse version before any version exists"
            raise ValueError(msg)
        return latest
