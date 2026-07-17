"""Dashboard runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_ENV_STORAGE_ROOT = "DASHBOARD_STORAGE_ROOT"


@dataclass(frozen=True, slots=True)
class DashboardSettings:
    """Resolved settings for one dashboard process."""

    storage_root: Path


def load_settings(*, storage_root: Path | None = None) -> DashboardSettings:
    """Load settings from an explicit path or ``DASHBOARD_STORAGE_ROOT``.

    Parameters
    ----------
    storage_root:
        Optional override (e.g. from the Streamlit sidebar). When omitted, the
        environment variable ``DASHBOARD_STORAGE_ROOT`` is required.
    """
    if storage_root is not None:
        root = storage_root.expanduser().resolve()
    else:
        raw = os.environ.get(_ENV_STORAGE_ROOT)
        if raw is None or not raw.strip():
            msg = (
                f"set {_ENV_STORAGE_ROOT} to the workspace root that contains "
                "market_data/ and research/, or pass storage_root explicitly"
            )
            raise ValueError(msg)
        root = Path(raw).expanduser().resolve()
    return DashboardSettings(storage_root=root)


def storage_root_status(settings: DashboardSettings) -> dict[str, bool]:
    """Return existence flags for expected top-level storage folders."""
    root = settings.storage_root
    return {
        "storage_root_exists": root.is_dir(),
        "market_data_exists": (root / "market_data").is_dir(),
        "research_exists": (root / "research").is_dir(),
    }
