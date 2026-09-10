"""Cross-cutting integration tests for the VPS dry-run worker (T002) and the read-only status API
(T003) sharing one on-disk :class:`JsonExecutionStateRepository` (SPRINT_062.md T006).

Each prior task already tests its own boundary in isolation:

- ``test_local_btc_futures.py`` exercises restart/refuse-to-start entirely through the worker's
  in-process runtime assembly (``create_local_btc_futures_dry_run_runtime``), never reading the
  result back through the status API.
- ``test_vps_status_api.py`` exercises the status handler entirely against a hand-built
  ``FakeExecutionStatusRepository`` / ``RuntimeStatusView``, never through a real on-disk document.
- ``test_run_vps_status_service.py`` reads a real (but hand-written) ``state.json`` through a real
  ``JsonExecutionStateRepository`` and the real aiohttp app, but never through anything the worker
  itself wrote.

None of those tie the worker's actual write path to the status API's actual read path through one
shared file, which is exactly the seam ADR-0035 depends on for restart, staleness and
unavailability to behave consistently for an operator watching both `docker compose logs` and the
public status card at the same time. These tests close that gap using real objects at every layer
(no HTTP, no Docker -- just the same in-process objects a real deployment wires together).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from trading_framework.application.execution import (
    LocalBtcFuturesDryRunConfig,
    RunLocalBtcFuturesDryRunRequest,
    create_local_btc_futures_dry_run_runtime,
    run_local_btc_futures_closed_bar_step,
    run_local_btc_futures_dry_run,
)
from trading_framework.application.execution.vps_status_api import (
    VpsExecutionStatusApiConfig,
    handle_vps_execution_status_request,
)
from trading_framework.core.exceptions import IncompatibleExecutionStateError
from trading_framework.core.types import Price, Volume
from trading_framework.execution import (
    ExecutionMode,
    PaperAccountSnapshot,
    PaperPosition,
    PositionSide,
    RuntimeHealth,
    RuntimeStatusSnapshot,
)
from trading_framework.infrastructure.storage.execution_state import JsonExecutionStateRepository
from trading_framework.market.models import MarketBar
from trading_framework.strategy import BtcFuturesDemoStrategyConfig
from trading_framework.time.clocks.fixed import FixedClock

NOW = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)


def _bar(close: str, index: int) -> MarketBar:
    close_price = Price(Decimal(close))
    observed_at = NOW + timedelta(minutes=index)
    return MarketBar(
        open=close_price,
        high=close_price,
        low=close_price,
        close=close_price,
        volume=Volume(1),
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
    )


def _status_config(
    runtime_id: str, *, stale_after_seconds: int = 60
) -> VpsExecutionStatusApiConfig:
    return VpsExecutionStatusApiConfig(
        runtime_id=runtime_id, stale_after_seconds=stale_after_seconds
    )


def test_restart_restores_position_and_status_api_serves_it_through_the_same_file(
    tmp_path: Path,
) -> None:
    """A position opened before a restart, restored by the worker (T002), must be exactly what the
    status API (T003) reports afterwards -- through the one shared ``state.json``, not a mock."""
    state_path = tmp_path / "state"
    config = LocalBtcFuturesDryRunConfig(
        event_log_path=tmp_path / "events.jsonl",
        state_repository_path=state_path,
        strategy_config=BtcFuturesDemoStrategyConfig(ema_period=2),
    )
    runtime = create_local_btc_futures_dry_run_runtime(config, clock=FixedClock(NOW))
    result = run_local_btc_futures_closed_bar_step(
        runtime, (_bar("100", 0), _bar("100", 1), _bar("101", 2))
    )
    assert result.decision_result.order_submitted

    # Simulate a Compose restart: a fresh runtime object reads the same volume.
    restarted = create_local_btc_futures_dry_run_runtime(config, clock=FixedClock(NOW))
    assert restarted.initial_state.position.quantity == Decimal("0.001")

    repository = JsonExecutionStateRepository(state_path)
    response = handle_vps_execution_status_request(
        "GET",
        config=_status_config(config.runtime_id),
        repository=repository,
        now=NOW,
    )

    assert response.status_code == 200
    assert response.body["status"] == "running"
    assert response.body["current_position"]["side"] == "long"
    assert response.body["current_position"]["quantity"] == "0.001"


def test_stale_heartbeat_written_by_the_worker_is_reported_stale_by_the_status_api(
    tmp_path: Path,
) -> None:
    """Full write -> read roundtrip through JSON serialization (not a hand-built
    ``RuntimeStatusView``): a heartbeat older than the configured threshold, persisted exactly the
    way the worker persists it, must come back ``stale: true``."""
    state_path = tmp_path / "state"
    repository = JsonExecutionStateRepository(state_path)
    runtime_id = "btc-futures-dry-run-vps"
    old_heartbeat = NOW - timedelta(minutes=10)
    repository.save_runtime_status(
        RuntimeStatusSnapshot(
            runtime_id=runtime_id,
            mode=ExecutionMode.DRY_RUN,
            status=RuntimeHealth.RUNNING,
            provider="binance_usdm",
            symbol="BTCUSDT",
            last_heartbeat_at=old_heartbeat,
            feed_connection_state="connected",
            feed_reconnect_count=0,
        )
    )

    response = handle_vps_execution_status_request(
        "GET",
        config=_status_config(runtime_id, stale_after_seconds=60),
        repository=repository,
        now=NOW,
    )

    assert response.status_code == 200
    assert response.body["stale"] is True
    assert response.body["last_heartbeat_at"] == old_heartbeat.isoformat()
    # Still labelled "running" by the worker -- the status API adds `stale` on top rather than
    # overwriting the underlying health value (ADR-0035 SS3.5): the dashboard is what decides how
    # to badge a stale-but-nominally-running snapshot.
    assert response.body["status"] == "running"


def test_incompatible_state_refuses_restart_but_status_api_still_serves_the_last_known_snapshot(
    tmp_path: Path,
) -> None:
    """Refuse-to-start (ADR-0035 SS4.4) does not touch the persisted document at all: it raises
    before the runtime starts. An operator polling the status API during that window sees the
    worker's last known (and, given enough elapsed time, increasingly stale) status -- not a 503,
    not a fabricated FAILED -- because the file itself is perfectly readable, just semantically
    incompatible with the *new* configuration the status API knows nothing about."""
    state_path = tmp_path / "state"
    repository = JsonExecutionStateRepository(state_path)
    runtime_id = "btc-futures-dry-run-vps"
    repository.save_runtime_status(
        RuntimeStatusSnapshot(
            runtime_id=runtime_id,
            mode=ExecutionMode.DRY_RUN,
            status=RuntimeHealth.RUNNING,
            provider="binance_usdm",
            symbol="BTCUSDT",
            last_heartbeat_at=NOW,
        )
    )
    repository.save_position(
        runtime_id,
        PaperPosition(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("0.001"),
            average_entry_price=Price(Decimal("100")),
            mark_price=Price(Decimal("100")),
            unrealized_pnl=Decimal("0"),
            updated_at=NOW,
        ),
    )
    repository.save_account(
        runtime_id,
        PaperAccountSnapshot(
            account_id="paper-btc-futures",
            currency="USDT",
            starting_equity=Decimal("10000"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            equity=Decimal("10000"),
            updated_at=NOW,
        ),
    )

    incompatible_config = LocalBtcFuturesDryRunConfig(
        event_log_path=tmp_path / "events.jsonl",
        state_repository_path=state_path,
        runtime_id=runtime_id,
        currency="EUR",  # deliberately incompatible with the persisted "USDT" account
    )
    with pytest.raises(IncompatibleExecutionStateError, match="currency mismatch"):
        create_local_btc_futures_dry_run_runtime(incompatible_config, clock=FixedClock(NOW))

    later = NOW + timedelta(hours=1)
    response = handle_vps_execution_status_request(
        "GET",
        config=_status_config(runtime_id, stale_after_seconds=60),
        repository=repository,
        now=later,
    )

    assert response.status_code == 200
    assert response.body["status"] == "running"
    assert response.body["stale"] is True, (
        "an hour with no fresh heartbeat because the worker refused to restart must surface as "
        "stale, not as a silently-current snapshot"
    )


def test_corrupt_state_refuses_worker_restart_and_status_api_returns_503_from_the_same_file(
    tmp_path: Path,
) -> None:
    """A genuinely corrupt on-disk document -- written by hand here, not a mocked exception --
    must fail closed identically for both consumers of ``JsonExecutionStateRepository``: the
    worker refuses to start (exit code 2 at the entry-point layer) and the status API returns 503,
    because they hit the exact same unreadable file."""
    state_path = tmp_path / "state"
    runtime_id = "btc-futures-dry-run-vps"
    state_file = state_path / runtime_id / "state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text("{not valid json", encoding="utf-8")

    config = LocalBtcFuturesDryRunConfig(
        event_log_path=tmp_path / "events.jsonl",
        state_repository_path=state_path,
        runtime_id=runtime_id,
    )
    with pytest.raises(IncompatibleExecutionStateError, match="unreadable"):
        create_local_btc_futures_dry_run_runtime(config, clock=FixedClock(NOW))

    repository = JsonExecutionStateRepository(state_path)
    response = handle_vps_execution_status_request(
        "GET",
        config=_status_config(runtime_id),
        repository=repository,
        now=NOW,
    )

    assert response.status_code == 503
    assert response.body["error"] == "status_unavailable"
    # Never leaks the raw file path or JSON parser error text.
    assert str(state_file) not in str(response.body)


def test_no_state_yet_worker_starts_fresh_and_status_api_reports_404(tmp_path: Path) -> None:
    """A pristine execution-state volume (first deploy, or a deliberately reset one) must be
    honest at both layers: the worker starts fresh (never silently reuses stale defaults) and the
    status API reports 404 (never a fabricated empty 200 snapshot), whichever order they're
    checked in."""
    state_path = tmp_path / "state"
    runtime_id = "btc-futures-dry-run-vps"
    repository = JsonExecutionStateRepository(state_path)

    response = handle_vps_execution_status_request(
        "GET",
        config=_status_config(runtime_id),
        repository=repository,
        now=NOW,
    )
    assert response.status_code == 404

    config = LocalBtcFuturesDryRunConfig(
        event_log_path=tmp_path / "events.jsonl",
        state_repository_path=state_path,
        runtime_id=runtime_id,
    )
    runtime = create_local_btc_futures_dry_run_runtime(config, clock=FixedClock(NOW))
    assert runtime.initial_state.account.equity == Decimal("10000")
    assert runtime.initial_state.position.quantity == Decimal("0")


def test_graceful_stop_persists_stopped_and_status_api_reports_it_honestly(tmp_path: Path) -> None:
    """T002's graceful-stop lifecycle (persist ``STOPPED``, exit 0) and T003's status API, wired
    through the same repository the worker's own loop uses -- not a re-seeded fake."""
    event_log_path = tmp_path / "events.jsonl"
    state_path = tmp_path / "state"
    result = run_local_btc_futures_dry_run(
        RunLocalBtcFuturesDryRunRequest(
            config=LocalBtcFuturesDryRunConfig(
                event_log_path=event_log_path,
                state_repository_path=state_path,
            ),
            duration_minutes=0,
            heartbeat_seconds=1,
        ),
        clock=FixedClock(NOW),
    )
    assert result.stopped_status.status.value == "stopped"

    repository = JsonExecutionStateRepository(state_path)
    response = handle_vps_execution_status_request(
        "GET",
        config=_status_config(result.runtime.config.runtime_id),
        repository=repository,
        now=NOW,
    )

    assert response.status_code == 200
    assert response.body["status"] == "stopped"


def test_failed_status_persisted_by_the_worker_is_reported_failed_by_the_status_api(
    tmp_path: Path,
) -> None:
    """An unrecoverable-error ``FAILED`` snapshot (ADR-0035 SS4.3), once persisted through the
    real repository, must surface through the real status handler as ``status: "failed"`` --
    closing the one worker-lifecycle terminal state the other integration tests in this file
    don't already exercise (fresh/restored/stale/stopped/incompatible/corrupt/absent)."""
    state_path = tmp_path / "state"
    repository = JsonExecutionStateRepository(state_path)
    runtime_id = "btc-futures-dry-run-vps"
    repository.save_runtime_status(
        RuntimeStatusSnapshot(
            runtime_id=runtime_id,
            mode=ExecutionMode.DRY_RUN,
            status=RuntimeHealth.FAILED,
            provider="binance_usdm",
            symbol="BTCUSDT",
            last_heartbeat_at=NOW,
        )
    )

    response = handle_vps_execution_status_request(
        "GET",
        config=_status_config(runtime_id),
        repository=repository,
        now=NOW,
    )

    assert response.status_code == 200
    assert response.body["status"] == "failed"
