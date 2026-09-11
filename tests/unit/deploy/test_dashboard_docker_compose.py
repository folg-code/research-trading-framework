"""Structural checks for the VPS dashboard Compose stack (ADR-0036 SS1, SS4.5-4.7).

Parses the YAML directly (no ``docker`` dependency, so this runs anywhere pytest does) and asserts
the specific topology/isolation properties ADR-0036 requires: no port surface for the worker or
status service, read-only vs. read-write state-volume ownership, and no state-volume access from
``dashboard``. Where the Docker CLI is available, an additional smoke test also runs
``docker compose config --quiet`` to catch YAML/structural errors the schema itself would reject.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]

COMPOSE_PATH = (
    Path(__file__).resolve().parents[3] / "apps" / "dashboard" / "deploy" / "docker-compose.yml"
)
STATE_VOLUME = "dry_run_execution_state"


def _load_compose() -> dict[str, Any]:
    loaded: Any = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _service(compose: dict[str, Any], name: str) -> dict[str, Any]:
    service: Any = compose["services"][name]
    assert isinstance(service, dict)
    return service


def _volume_mount(service: dict[str, Any], volume_name: str) -> dict[str, Any] | None:
    for mount in service.get("volumes", []):
        if isinstance(mount, dict) and mount.get("source") == volume_name:
            return mount
    return None


def test_compose_file_parses_as_yaml() -> None:
    compose = _load_compose()
    assert "dry-run-worker" in compose["services"]
    assert "dry-run-status" in compose["services"]


def test_dry_run_worker_has_no_port_surface() -> None:
    worker = _service(_load_compose(), "dry-run-worker")
    assert "ports" not in worker
    assert "expose" not in worker


def test_dry_run_status_is_expose_only_never_published() -> None:
    status = _service(_load_compose(), "dry-run-status")
    assert "ports" not in status
    assert status.get("expose") == ["8090"]


def test_state_volume_is_read_only_for_status_and_read_write_for_worker() -> None:
    compose = _load_compose()
    worker_mount = _volume_mount(_service(compose, "dry-run-worker"), STATE_VOLUME)
    status_mount = _volume_mount(_service(compose, "dry-run-status"), STATE_VOLUME)

    assert worker_mount is not None
    assert status_mount is not None
    assert worker_mount.get("read_only") is not True
    assert status_mount.get("read_only") is True


def test_dashboard_has_no_state_volume_mount() -> None:
    dashboard = _service(_load_compose(), "dashboard")
    assert _volume_mount(dashboard, STATE_VOLUME) is None


def test_dashboard_does_not_require_status_service_healthy() -> None:
    dashboard = _service(_load_compose(), "dashboard")
    depends_on = dashboard.get("depends_on")
    if depends_on is None:
        return
    status_dependency = depends_on.get("dry-run-status") if isinstance(depends_on, dict) else None
    if status_dependency is None:
        return
    assert status_dependency.get("condition") != "service_healthy"


def test_caddy_and_worker_do_not_share_a_network_with_status() -> None:
    compose = _load_compose()
    caddy_networks = set(_service(compose, "caddy").get("networks", []))
    worker_networks = set(_service(compose, "dry-run-worker").get("networks", []))
    status_networks = set(_service(compose, "dry-run-status").get("networks", []))

    assert caddy_networks.isdisjoint(status_networks)
    assert worker_networks.isdisjoint(status_networks)
    assert worker_networks.isdisjoint(caddy_networks)


def test_status_network_is_internal_blocking_its_own_outbound_egress() -> None:
    # Stricter than ADR-0036's literal minimum (SS1.4 only requires caddy/worker isolation from
    # `status`): a compromised dry-run-status container should not gain outbound internet access
    # either. Regression-guards the deliberate `internal: true` hardening.
    compose = _load_compose()
    status_network = compose["networks"]["status"]
    assert isinstance(status_network, dict)
    assert status_network.get("internal") is True


def test_worker_and_status_declare_bounded_restart_policy_and_resource_limits() -> None:
    compose = _load_compose()
    for name in ("dry-run-worker", "dry-run-status"):
        service = _service(compose, name)
        restart = service.get("restart", "")
        assert restart.startswith("on-failure"), f"{name} restart policy: {restart!r}"
        assert "mem_limit" in service, f"{name} is missing an explicit memory limit"
        assert "cpus" in service, f"{name} is missing an explicit CPU limit"
        assert "logging" in service, f"{name} is missing an explicit logging driver"


@pytest.mark.skipif(shutil.which("docker") is None, reason="docker CLI not available")
def test_docker_compose_config_accepts_the_file() -> None:
    result = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_PATH), "config", "--quiet"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
