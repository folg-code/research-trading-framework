"""Continuous OHLCV derivation repository helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path

from trading_framework.infrastructure.storage.continuous_ohlcv_manifest_store import (
    ContinuousOhlcvManifest,
    write_continuous_ohlcv_manifest,
)
from trading_framework.infrastructure.storage.paths import continuous_ohlcv_manifest_path
from trading_framework.market.datasets import DatasetRef


def compute_continuous_ohlcv_source_fingerprint(
    *,
    source_continuous_trades_ref: str,
    source_continuous_manifest_fingerprint: str,
    schema_version: str,
    derivation_method: str,
    derivation_version: str,
    builder_version: str,
    target_timeframe: str,
    start_session: str,
    end_session: str,
) -> str:
    """Compute a stable fingerprint for continuous OHLCV rebuild decisions."""
    payload = "|".join(
        [
            source_continuous_trades_ref,
            source_continuous_manifest_fingerprint,
            schema_version,
            derivation_method,
            derivation_version,
            builder_version,
            target_timeframe,
            start_session,
            end_session,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_dataset_continuous_ohlcv_manifest(
    root: Path,
    dataset_ref: DatasetRef,
    manifest: ContinuousOhlcvManifest,
) -> Path:
    """Persist the continuous OHLCV manifest for one dataset version."""
    return write_continuous_ohlcv_manifest(
        continuous_ohlcv_manifest_path(root, dataset_ref),
        manifest,
    )
