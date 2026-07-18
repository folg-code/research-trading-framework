"""Storage fingerprint and Streamlit-oriented cache key helpers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class StorageFingerprint:
    """Cheap workspace fingerprint for Streamlit cache invalidation."""

    token: str
    storage_root: str


def compute_storage_fingerprint(storage_root: Path) -> StorageFingerprint:
    """Hash selected top-level research/market_data mtimes (not full tree walk).

    Deep content hashing would be too expensive for UI cache keys. This fingerprint
    changes when catalog roots gain or lose children or when their mtimes move.
    """
    root = storage_root.expanduser().resolve()
    digest = hashlib.sha256()
    digest.update(str(root).encode("utf-8"))
    for relative in ("research", "market_data"):
        path = root / relative
        digest.update(relative.encode("utf-8"))
        if not path.exists():
            digest.update(b"missing")
            continue
        digest.update(str(path.stat().st_mtime_ns).encode("ascii"))
        if path.is_dir():
            try:
                children = sorted(path.iterdir(), key=lambda item: item.name)
            except OSError:
                children = []
            for child in children[:64]:
                digest.update(child.name.encode("utf-8", errors="replace"))
                try:
                    digest.update(str(child.stat().st_mtime_ns).encode("ascii"))
                except OSError:
                    digest.update(b"err")
    return StorageFingerprint(token=digest.hexdigest()[:24], storage_root=str(root))


def cache_key_parts(
    *,
    fingerprint: StorageFingerprint,
    window_start: str | None = None,
    window_end: str | None = None,
    timeframe: str | None = None,
    run_id: str | None = None,
) -> tuple[str, ...]:
    """Build a stable tuple suitable for ``st.cache_data`` hash inputs."""
    return (
        fingerprint.token,
        fingerprint.storage_root,
        window_start or "",
        window_end or "",
        timeframe or "",
        run_id or "",
    )
