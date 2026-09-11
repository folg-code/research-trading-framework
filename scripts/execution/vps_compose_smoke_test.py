"""Container smoke test for the VPS dry-run Compose stack (SPRINT_062.md T006, ADR-0036).

T004's Compose topology (``apps/dashboard/deploy/docker-compose.yml``) is already checked
structurally, without Docker, by ``tests/unit/deploy/test_dashboard_docker_compose.py`` (parses
the YAML) and ``docker compose config --quiet`` (schema validation only). Neither actually starts
the stack. This script builds and runs it for real and asserts the properties T004's manual QA
session checked once, ad hoc:

1. ``dry-run-worker`` and ``dry-run-status`` reach a healthy state.
2. The state volume is genuinely read-only inside ``dry-run-status`` at the OS level, not merely
   ``read_only: true`` in the YAML.
3. Network isolation actually holds at runtime: ``dry-run-worker`` cannot reach ``dry-run-status``,
   ``dry-run-status`` cannot reach the public internet, and ``dashboard`` *can* reach
   ``dry-run-status``.

Not run in CI by default (building images and starting containers is slow and requires a working
Docker daemon). Opt in locally or in a dedicated CI job with:

    python -m scripts.execution.vps_compose_smoke_test

Exit codes: ``0`` all checks passed; ``1`` a check failed or Docker is unavailable; ``2`` invalid
usage. Always tears the stack down (`docker compose down --volumes`) before returning, even on
failure.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

COMPOSE_FILE = (
    Path(__file__).resolve().parents[2] / "apps" / "dashboard" / "deploy" / "docker-compose.yml"
)
HEALTH_TIMEOUT_SECONDS = 300
HEALTH_POLL_SECONDS = 5
MONITORED_SERVICES = ("dry-run-worker", "dry-run-status", "dashboard")


class SmokeTestFailure(RuntimeError):
    """A single smoke-test assertion failed."""


def _compose(
    *args: str, check: bool = True, timeout: int = 120
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
    )


def _container_id(service: str) -> str:
    result = _compose("ps", "-q", service)
    container_id = result.stdout.strip()
    if not container_id:
        raise SmokeTestFailure(f"no running container for service {service!r}")
    return container_id


def _health_status(service: str) -> str:
    container_id = _container_id(service)
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_id],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return result.stdout.strip()


def _wait_for_healthy(service: str, *, timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_status = "unknown"
    while time.monotonic() < deadline:
        last_status = _health_status(service)
        if last_status == "healthy":
            return
        if last_status == "unhealthy":
            raise SmokeTestFailure(f"{service} reported unhealthy before becoming healthy")
        time.sleep(HEALTH_POLL_SECONDS)
    raise SmokeTestFailure(
        f"{service} did not become healthy within {timeout_seconds}s (last status: {last_status})"
    )


def _exec_python(service: str, code: str, *, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "exec", "-T", service, "python", "-c", code],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _check_state_volume_read_only(service: str) -> None:
    """Confirm the ``read_only: true`` mount is enforced by the OS, not merely declared in YAML."""
    probe_path = "/var/lib/trading-framework/btc-futures-dry-run/_smoke_write_probe"
    probe = (
        "import pathlib, sys\n"
        f"target = pathlib.Path({probe_path!r})\n"
        "try:\n"
        "    target.write_text('x')\n"
        "except OSError:\n"
        "    sys.exit(0)\n"
        "target.unlink(missing_ok=True)\n"
        "sys.exit(1)\n"
    )
    result = _exec_python(service, probe)
    if result.returncode != 0:
        raise SmokeTestFailure(
            f"{service} was able to write to its read-only state mount "
            f"(returncode={result.returncode})"
        )


def _check_cannot_reach(service: str, url: str, *, reason: str) -> None:
    probe = f"import urllib.request\nurllib.request.urlopen({url!r}, timeout=5)\n"
    result = _exec_python(service, probe, timeout=15)
    if result.returncode == 0:
        raise SmokeTestFailure(f"{service} unexpectedly reached {url} ({reason} should block this)")


def _check_can_reach(service: str, url: str) -> None:
    probe = (
        f"import urllib.request\n"
        f"resp = urllib.request.urlopen({url!r}, timeout=5)\n"
        f"assert resp.status == 200, resp.status\n"
    )
    result = _exec_python(service, probe, timeout=15)
    if result.returncode != 0:
        raise SmokeTestFailure(
            f"{service} could not reach {url} (stdout={result.stdout!r} stderr={result.stderr!r})"
        )


def run_smoke_test() -> None:
    """Build, start, verify and tear down the VPS Compose stack. Raises on any failure."""
    print(f"[smoke] building and starting stack from {COMPOSE_FILE}")
    _compose("up", "-d", "--build", timeout=900)
    try:
        for service in MONITORED_SERVICES:
            print(f"[smoke] waiting for {service} to become healthy")
            _wait_for_healthy(service, timeout_seconds=HEALTH_TIMEOUT_SECONDS)

        print("[smoke] checking state volume is read-only in dry-run-status")
        _check_state_volume_read_only("dry-run-status")

        print("[smoke] checking dry-run-worker cannot reach dry-run-status")
        _check_cannot_reach(
            "dry-run-worker",
            "http://dry-run-status:8090/healthz",
            reason="worker/status network isolation",
        )

        print("[smoke] checking dry-run-status cannot reach the public internet")
        _check_cannot_reach(
            "dry-run-status",
            "https://api.binance.com/api/v3/ping",
            reason="the status network is internal:true",
        )

        print("[smoke] checking dashboard can reach dry-run-status")
        _check_can_reach("dashboard", "http://dry-run-status:8090/healthz")

        print("[smoke] all checks passed")
    finally:
        print("[smoke] tearing down stack")
        _compose("down", "--volumes", "--remove-orphans", timeout=120, check=False)


def main() -> int:
    if shutil.which("docker") is None:
        print("docker CLI not found; cannot run the compose smoke test", file=sys.stderr)
        return 1
    try:
        run_smoke_test()
    except SmokeTestFailure as exc:
        print(f"[smoke] FAILED: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"[smoke] FAILED: {exc} (stderr={exc.stderr})", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired as exc:
        print(f"[smoke] FAILED: timed out ({exc})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
