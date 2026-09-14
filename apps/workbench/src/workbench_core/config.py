"""Bind address and storage-root configuration for workbench-api.

ADR-0037 section 4: workbench-api binds to loopback only. No authentication,
no authorization roles, no TLS -- a non-loopback bind host is refused at
startup rather than silently accepted.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from trading_framework.core.exceptions import ConfigurationError

DEFAULT_HOST: Final = "127.0.0.1"
DEFAULT_PORT: Final = 8765
DEFAULT_STORAGE_ROOT: Final = "user_data"

_STORAGE_ROOT_ENV: Final = "TRADING_WORKBENCH_STORAGE_ROOT"
_HOST_ENV: Final = "TRADING_WORKBENCH_HOST"
_PORT_ENV: Final = "TRADING_WORKBENCH_PORT"
_LOOPBACK_HOSTS: Final = frozenset({"127.0.0.1", "localhost", "::1"})


@dataclass(frozen=True, slots=True)
class WorkbenchApiConfig:
    """Loopback-only bind address and the operator's storage root."""

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    storage_root: Path = Path(DEFAULT_STORAGE_ROOT)

    def __post_init__(self) -> None:
        if self.host not in _LOOPBACK_HOSTS:
            msg = (
                f"workbench-api must bind to a loopback address, got {self.host!r} "
                f"(ADR-0037 section 4); allowed: {sorted(_LOOPBACK_HOSTS)}"
            )
            raise ConfigurationError(msg)
        if not 1 <= self.port <= 65535:
            msg = "workbench-api port must be between 1 and 65535"
            raise ConfigurationError(msg)


def load_workbench_api_config(env: Mapping[str, str]) -> WorkbenchApiConfig:
    """Load bind address and storage root from the environment.

    ``TRADING_WORKBENCH_STORAGE_ROOT`` is required: there is no framework-wide
    default workspace an operator would expect this to fall back to silently.
    """
    storage_root_raw = env.get(_STORAGE_ROOT_ENV, "").strip()
    if not storage_root_raw:
        msg = f"{_STORAGE_ROOT_ENV} is required"
        raise ConfigurationError(msg)
    host = env.get(_HOST_ENV, DEFAULT_HOST).strip() or DEFAULT_HOST
    port = _int(env, _PORT_ENV, DEFAULT_PORT)
    return WorkbenchApiConfig(host=host, port=port, storage_root=Path(storage_root_raw))


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        msg = f"{name} must be an integer"
        raise ConfigurationError(msg) from exc
