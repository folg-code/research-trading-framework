"""Checksum helpers for external archive imports."""

import hashlib
from pathlib import Path


def compute_source_checksum_sha256(path: Path) -> str:
    """Return the hex SHA-256 digest of the raw archive bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
