"""Continuous trades repository helpers."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from trading_framework.infrastructure.storage.continuous_manifest_store import (
    ContinuousTradesManifest,
    write_continuous_trades_manifest,
)
from trading_framework.infrastructure.storage.paths import continuous_trades_manifest_path
from trading_framework.market.datasets import DatasetRef


def compute_continuous_source_fingerprint(
    *,
    roll_schedule_fingerprint: str,
    roll_schedule_version: int,
    contract_dataset_refs: Sequence[str],
    schema_version: str,
    builder_version: str,
    policy_slug: str,
    start_session: date,
    end_session: date,
) -> str:
    """Compute a stable fingerprint for continuous trades rebuild decisions."""
    payload = "|".join(
        [
            policy_slug,
            str(roll_schedule_version),
            roll_schedule_fingerprint,
            schema_version,
            builder_version,
            start_session.isoformat(),
            end_session.isoformat(),
            *sorted(contract_dataset_refs),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_dataset_continuous_manifest(
    root: Path,
    dataset_ref: DatasetRef,
    manifest: ContinuousTradesManifest,
) -> Path:
    """Persist the continuous manifest for one dataset version."""
    return write_continuous_trades_manifest(
        continuous_trades_manifest_path(root, dataset_ref),
        manifest,
    )
