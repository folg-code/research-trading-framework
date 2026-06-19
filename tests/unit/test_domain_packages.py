"""Domain package import smoke tests."""

import importlib

import pytest

DOMAIN_PACKAGES = [
    "trading_framework.core",
    "trading_framework.time",
    "trading_framework.market",
    "trading_framework.market_analysis",
    "trading_framework.strategy",
    "trading_framework.research",
    "trading_framework.execution",
    "trading_framework.events",
    "trading_framework.config",
    "trading_framework.infrastructure",
    "trading_framework.application",
]


@pytest.mark.parametrize("package_name", DOMAIN_PACKAGES)
def test_domain_package_imports(package_name: str) -> None:
    module = importlib.import_module(package_name)
    assert module is not None
