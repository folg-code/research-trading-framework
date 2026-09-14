"""Unit tests for workbench_core.config (Sprint 064 T004)."""

from __future__ import annotations

from pathlib import Path

import pytest
from trading_framework.core.exceptions import ConfigurationError

from workbench_core.config import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    WorkbenchApiConfig,
    load_workbench_api_config,
)


def test_default_host_is_loopback() -> None:
    config = WorkbenchApiConfig(storage_root=Path("user_data"))
    assert config.host == DEFAULT_HOST
    assert config.host == "127.0.0.1"


@pytest.mark.parametrize("host", ["0.0.0.0", "10.0.0.5", "example.com"])
def test_non_loopback_host_is_refused(host: str) -> None:
    with pytest.raises(ConfigurationError, match="loopback"):
        WorkbenchApiConfig(host=host, storage_root=Path("user_data"))


@pytest.mark.parametrize("port", [0, -1, 65536, 100_000])
def test_invalid_port_is_refused(port: int) -> None:
    with pytest.raises(ConfigurationError, match="port"):
        WorkbenchApiConfig(port=port, storage_root=Path("user_data"))


def test_load_config_requires_storage_root() -> None:
    with pytest.raises(ConfigurationError, match="TRADING_WORKBENCH_STORAGE_ROOT"):
        load_workbench_api_config({})


def test_load_config_from_environment() -> None:
    config = load_workbench_api_config(
        {
            "TRADING_WORKBENCH_STORAGE_ROOT": "/tmp/workspace",
            "TRADING_WORKBENCH_HOST": "localhost",
            "TRADING_WORKBENCH_PORT": "9001",
        }
    )
    assert config.storage_root == Path("/tmp/workspace")
    assert config.host == "localhost"
    assert config.port == 9001


def test_load_config_defaults_host_and_port() -> None:
    config = load_workbench_api_config({"TRADING_WORKBENCH_STORAGE_ROOT": "/tmp/workspace"})
    assert config.host == DEFAULT_HOST
    assert config.port == DEFAULT_PORT


def test_load_config_rejects_non_integer_port() -> None:
    with pytest.raises(ConfigurationError, match="integer"):
        load_workbench_api_config(
            {
                "TRADING_WORKBENCH_STORAGE_ROOT": "/tmp/workspace",
                "TRADING_WORKBENCH_PORT": "not-a-number",
            }
        )
