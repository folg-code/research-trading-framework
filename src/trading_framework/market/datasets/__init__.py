"""Market dataset identity and versioning.

MVP dataset identity algorithm (Sprint 002 / PRB-001 partial resolution)
-----------------------------------------------------------------------

Logical identity
~~~~~~~~~~~~~~~~

``DatasetId`` is a stable logical key composed of:

- ``instrument_id``
- ``data_type`` (for example ``ohlcv``)
- ``timeframe``
- ``provider``
- ``source_id``

Versioning
~~~~~~~~~~

``DatasetRef = (DatasetId, version)`` where ``version`` is a positive integer
monotonically allocated per ``DatasetId``.

A **new version** is required when a **material semantic change** occurs:

- source data changed,
- records corrected,
- normalization logic changed,
- schema semantics changed,
- validation outcome changed.

A **new version is not required** for a physical rewrite that preserves identical
logical content (same semantic fingerprint / checksum at publication time).

Examples
~~~~~~~~

1. **Unchanged physical rewrite** — Parquet files are rewritten for compaction but
   bar content and normalization version are unchanged. Reuse the existing version.

2. **Corrected bar** — A bad OHLC row is fixed in the source CSV. Allocate the next
   version for the same ``DatasetId``.

3. **Changed normalization** — CSV timestamps were previously interpreted as interval
   end and are now normalized as interval start. Allocate the next version because
   semantic bar timing changed.
"""

from trading_framework.market.datasets.identity import DatasetId, DatasetRef
from trading_framework.market.datasets.lifecycle import (
    DatasetLifecycleState,
    assert_published_is_immutable,
    transition_dataset_lifecycle,
)
from trading_framework.market.datasets.metadata import DatasetMetadata, ValidationStatus
from trading_framework.market.datasets.versioning import (
    DatasetVersionAllocator,
    DatasetVersionPolicy,
    InMemoryDatasetVersionAllocator,
    MaterialChangeReason,
)

__all__ = [
    "DatasetId",
    "DatasetLifecycleState",
    "DatasetMetadata",
    "DatasetRef",
    "DatasetVersionAllocator",
    "DatasetVersionPolicy",
    "InMemoryDatasetVersionAllocator",
    "MaterialChangeReason",
    "ValidationStatus",
    "assert_published_is_immutable",
    "transition_dataset_lifecycle",
]
