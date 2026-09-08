"""Dashboard runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_ENV_STORAGE_ROOT = "DASHBOARD_STORAGE_ROOT"
_ENV_STATUS_URL = "DASHBOARD_STATUS_URL"

# Live Paper status is intentionally opt-in while the runtime is being migrated
# to the new VPS deployment. Configure DASHBOARD_STATUS_URL when the endpoint is
# available again.
DEFAULT_LIVE_PAPER_STATUS_URL: str | None = None


@dataclass(frozen=True, slots=True)
class DashboardSettings:
    """Resolved settings for one dashboard process."""

    storage_root: Path
    status_url: str | None = None


def load_settings(
    *,
    storage_root: Path | None = None,
    status_url: str | None = None,
) -> DashboardSettings:
    """Load settings from an explicit path or ``DASHBOARD_STORAGE_ROOT``.

    Parameters
    ----------
    storage_root:
        Optional override (e.g. from the Streamlit sidebar). When omitted, the
        environment variable ``DASHBOARD_STORAGE_ROOT`` is required.
    status_url:
        Optional read-only Live Paper status API URL. When omitted, uses
        ``DASHBOARD_STATUS_URL`` if set, otherwise ``DEFAULT_LIVE_PAPER_STATUS_URL``.
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
    resolved_status = _resolve_status_url(status_url)
    return DashboardSettings(storage_root=root, status_url=resolved_status)


def resolve_status_url(*, status_url: str | None = None) -> str | None:
    """Resolve status URL from override, env, or the built-in default."""
    return _resolve_status_url(status_url)


def storage_root_status(settings: DashboardSettings) -> dict[str, bool]:
    """Return existence flags for expected top-level storage folders."""
    root = settings.storage_root
    return {
        "storage_root_exists": root.is_dir(),
        "market_data_exists": (root / "market_data").is_dir(),
        "research_exists": (root / "research").is_dir(),
    }


def _resolve_status_url(status_url: str | None) -> str | None:
    if status_url is not None and status_url.strip():
        return status_url.strip()
    raw = os.environ.get(_ENV_STATUS_URL)
    if raw is not None and raw.strip():
        return raw.strip()
    return DEFAULT_LIVE_PAPER_STATUS_URL
