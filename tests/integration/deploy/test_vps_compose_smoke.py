"""Opt-in container smoke test for the VPS dry-run Compose stack (SPRINT_062.md T006).

Skipped by default (mirrors ``tests/integration/live_data/test_binance_futures_network_smoke.py``'s
opt-in-env-var pattern): building images and starting containers is slow and requires a working
Docker daemon, so this must never run unattended in a fast unit-test loop or a CI job that lacks
Docker. Run explicitly with:

    TRADING_FRAMEWORK_RUN_VPS_COMPOSE_SMOKE=1 \
        pytest tests/integration/deploy/test_vps_compose_smoke.py

or directly via ``python -m scripts.execution.vps_compose_smoke_test``.
"""

from __future__ import annotations

import os
import shutil

import pytest
from scripts.execution import vps_compose_smoke_test

RUN_ENV_VAR = "TRADING_FRAMEWORK_RUN_VPS_COMPOSE_SMOKE"

pytestmark = pytest.mark.docker


@pytest.mark.skipif(
    os.getenv(RUN_ENV_VAR) != "1",
    reason=f"set {RUN_ENV_VAR}=1 to run the VPS Compose container smoke test",
)
@pytest.mark.skipif(shutil.which("docker") is None, reason="docker CLI not available")
def test_vps_compose_stack_is_healthy_and_network_isolated() -> None:
    """Build, start, verify health/isolation and tear down the real Compose stack."""
    vps_compose_smoke_test.run_smoke_test()
