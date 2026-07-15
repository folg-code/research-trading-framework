"""Fingerprint helpers for robustness experiment configs."""

from __future__ import annotations

import hashlib
import json


def config_fingerprint(parameter_overrides: dict[str, str]) -> str:
    """Stable fingerprint for one grid cell parameter assignment."""
    payload = json.dumps(parameter_overrides, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def config_id_for_fingerprint(config_fingerprint_value: str, *, index: int) -> str:
    """Human-readable config id combining grid order and fingerprint."""
    return f"cell_{index:04d}_{config_fingerprint_value}"
