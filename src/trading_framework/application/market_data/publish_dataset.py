"""Publish a FINALIZED dataset version."""

from dataclasses import replace
from pathlib import Path

from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import (
    DatasetLifecycleState,
    DatasetRef,
    transition_dataset_lifecycle,
)
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock


def publish_dataset(
    dataset_ref: DatasetRef,
    *,
    storage_root: Path,
    registry: FileDatasetRegistry | None = None,
    clock: Clock | None = None,
) -> DatasetRef:
    """Transition a FINALIZED dataset version to PUBLISHED."""
    dataset_registry = registry or FileDatasetRegistry(storage_root)
    utc_clock = clock or SystemClock()
    metadata = dataset_registry.get(dataset_ref)
    lifecycle_status = transition_dataset_lifecycle(
        metadata.lifecycle_status,
        DatasetLifecycleState.PUBLISHED,
    )
    updated = replace(
        metadata,
        lifecycle_status=lifecycle_status,
        published_at=utc_clock.now(),
    )
    dataset_registry.update(updated)
    return dataset_ref
