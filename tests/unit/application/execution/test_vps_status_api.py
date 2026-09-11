"""Tests for the read-only VPS execution status API (execution.status.v1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_framework.application.execution.vps_status_api import (
    SCHEMA_VERSION,
    VpsExecutionStatusApiConfig,
    handle_vps_execution_status_request,
    handle_vps_status_health_check,
    load_vps_execution_status_api_config,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price
from trading_framework.execution import (
    ExecutionEventType,
    ExecutionMode,
    ExecutionReadModelQuery,
    PaperPosition,
    PositionSide,
    RecentBarView,
    RecentExecutionEventView,
    RuntimeHealth,
    RuntimeStatusView,
)

NOW = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)


@dataclass(slots=True)
class FakeExecutionStatusRepository:
    status: RuntimeStatusView | None
    query: ExecutionReadModelQuery | None = None
    error: Exception | None = None

    def latest_status_view(self, query: ExecutionReadModelQuery) -> RuntimeStatusView | None:
        self.query = query
        if self.error is not None:
            raise self.error
        return self.status

    def recent_events(self, query: ExecutionReadModelQuery) -> tuple[RecentExecutionEventView, ...]:
        return ()

    def recent_bars(self, query: ExecutionReadModelQuery) -> tuple[RecentBarView, ...]:
        return ()


def _status(**overrides: object) -> RuntimeStatusView:
    defaults: dict[str, object] = dict(
        runtime_id="vps-runtime-1",
        mode=ExecutionMode.DRY_RUN,
        provider="binance_usdm",
        symbol="BTCUSDT",
        status=RuntimeHealth.RUNNING,
        generated_at=NOW,
        last_heartbeat_at=NOW,
        last_market_event_at=NOW,
        last_price=Price(Decimal("65010")),
        current_signal="entry_signal_active",
        current_position=PaperPosition(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("0.001"),
            average_entry_price=Price(Decimal("65000")),
            mark_price=Price(Decimal("65010")),
            unrealized_pnl=Decimal("10"),
            updated_at=NOW,
        ),
        paper_equity=Decimal("10010"),
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("10"),
        feed_connection_state="connected",
        feed_reconnect_count=0,
    )
    defaults.update(overrides)
    return RuntimeStatusView(**defaults)  # type: ignore[arg-type]


def test_status_response_envelope_and_allowlisted_fields() -> None:
    config = VpsExecutionStatusApiConfig(runtime_id="vps-runtime-1")
    repository = FakeExecutionStatusRepository(status=_status())

    response = handle_vps_execution_status_request(
        "GET", config=config, repository=repository, now=NOW
    )

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.headers["Cache-Control"] == "no-store"
    body = response.body
    assert body["schema_version"] == SCHEMA_VERSION
    assert body["simulated"] is True
    assert body["generated_at"] == NOW.isoformat()
    assert body["runtime_id"] == "vps-runtime-1"
    assert body["mode"] == "dry_run"
    assert body["symbol"] == "BTCUSDT"
    assert body["status"] == "running"
    assert body["stale"] is False
    assert body["paper_equity"] == "10010"
    assert body["current_position"]["side"] == "long"
    assert repository.query == config.query


def test_status_response_marks_stale_after_threshold_but_still_returns_snapshot() -> None:
    config = VpsExecutionStatusApiConfig(runtime_id="vps-runtime-1", stale_after_seconds=60)
    old_heartbeat = NOW - timedelta(seconds=61)
    repository = FakeExecutionStatusRepository(status=_status(last_heartbeat_at=old_heartbeat))

    response = handle_vps_execution_status_request(
        "GET", config=config, repository=repository, now=NOW
    )

    assert response.status_code == 200
    assert response.body["stale"] is True
    assert response.body["last_heartbeat_at"] == old_heartbeat.isoformat()


def test_status_response_returns_404_when_no_state_for_runtime() -> None:
    config = VpsExecutionStatusApiConfig(runtime_id="vps-runtime-1")
    repository = FakeExecutionStatusRepository(status=None)

    response = handle_vps_execution_status_request(
        "GET", config=config, repository=repository, now=NOW
    )

    assert response.status_code == 404
    assert response.body["schema_version"] == SCHEMA_VERSION
    assert response.body["simulated"] is True
    assert response.body["error"] == "runtime_status_not_found"


def test_status_response_returns_405_for_non_get_with_allow_header() -> None:
    config = VpsExecutionStatusApiConfig(runtime_id="vps-runtime-1")
    repository = FakeExecutionStatusRepository(status=_status())

    for method in ("POST", "PUT", "DELETE", "PATCH"):
        response = handle_vps_execution_status_request(
            method, config=config, repository=repository, now=NOW
        )
        assert response.status_code == 405
        assert response.headers["Allow"] == "GET"
        assert response.body["schema_version"] == SCHEMA_VERSION
        assert response.body["simulated"] is True


def test_status_response_allows_head() -> None:
    config = VpsExecutionStatusApiConfig(runtime_id="vps-runtime-1")
    repository = FakeExecutionStatusRepository(status=_status())

    response = handle_vps_execution_status_request(
        "HEAD", config=config, repository=repository, now=NOW
    )

    assert response.status_code == 200


def test_status_response_returns_503_when_state_is_unreadable() -> None:
    config = VpsExecutionStatusApiConfig(runtime_id="vps-runtime-1")
    repository = FakeExecutionStatusRepository(
        status=None, error=ValidationError("unsupported execution state version")
    )

    response = handle_vps_execution_status_request(
        "GET", config=config, repository=repository, now=NOW
    )

    assert response.status_code == 503
    assert response.body["error"] == "status_unavailable"
    assert response.body["schema_version"] == SCHEMA_VERSION
    assert response.body["simulated"] is True
    # Never leaks the raw exception text.
    assert "unsupported execution state version" not in str(response.body)


@pytest.mark.parametrize(
    ("raw_error", "expected_code"),
    [
        ("Connection timed out after 30s", "connect_timeout"),
        ("connection closed by peer wss://stream.binance.com/ws", "connection_closed"),
        ("WebSocket protocol handshake failed", "protocol_error"),
        ("something totally unexpected happened", "unknown"),
        (None, None),
    ],
)
def test_feed_last_error_is_mapped_to_closed_vocabulary_code(
    raw_error: str | None, expected_code: str | None
) -> None:
    config = VpsExecutionStatusApiConfig(runtime_id="vps-runtime-1")
    repository = FakeExecutionStatusRepository(status=_status(feed_last_error=raw_error))

    response = handle_vps_execution_status_request(
        "GET", config=config, repository=repository, now=NOW
    )

    assert response.body["feed_last_error_code"] == expected_code
    assert "feed_last_error" not in response.body
    if raw_error is not None:
        assert raw_error not in str(response.body)


def test_runtime_failed_event_payload_message_is_never_emitted() -> None:
    """`RUNTIME_FAILED`'s ``message`` payload value is raw exception text
    (``binance_local_btc_futures.py`` calls ``session.fail(message=str(exc)[:500])``), which
    ``LocalExecutionRuntimeSession.fail`` persists verbatim into the event payload. It must never
    reach the public response, structurally, not merely be truncated (ADR-0036 section 3.3/3.4).
    """
    leaking_message = (
        "ConnectionError: wss://stream.binance.com:9443/ws/btcusdt@aggTrade "
        "unreachable from host vps-prod-01.internal at /var/lib/execution-state"
    )
    event = RecentExecutionEventView(
        event_id="btc-futures-dry-run-vps-000042-runtime_failed",
        event_type=ExecutionEventType.RUNTIME_FAILED,
        occurred_at=NOW,
        symbol="BTCUSDT",
        payload={
            "runtime_id": "btc-futures-dry-run-vps",
            "status": "failed",
            "message": leaking_message,
            "simulated": "true",
        },
    )
    config = VpsExecutionStatusApiConfig(runtime_id="vps-runtime-1")
    repository = FakeExecutionStatusRepository(status=_status(recent_events=(event,)))

    response = handle_vps_execution_status_request(
        "GET", config=config, repository=repository, now=NOW
    )

    recent_events = response.body["recent_events"]
    assert len(recent_events) == 1
    payload = recent_events[0]["payload"]
    assert payload is not None
    assert "message" not in payload
    assert payload == {
        "runtime_id": "btc-futures-dry-run-vps",
        "status": "failed",
        "simulated": "true",
    }
    # Never leaks anywhere in the body, not just under the "message" key.
    assert leaking_message not in str(response.body)
    assert "wss://" not in str(response.body)
    assert "vps-prod-01.internal" not in str(response.body)
    assert "/var/lib/execution-state" not in str(response.body)


@pytest.mark.parametrize("free_text_key", ["message", "reason", "feed_last_error"])
def test_event_payload_free_text_keys_are_always_dropped(free_text_key: str) -> None:
    """Every known free-text payload key is dropped regardless of which event type carries it."""
    event = RecentExecutionEventView(
        event_id="btc-futures-dry-run-vps-000001-order_intent_created",
        event_type=ExecutionEventType.ORDER_INTENT_CREATED,
        occurred_at=NOW,
        symbol="BTCUSDT",
        payload={
            "runtime_id": "btc-futures-dry-run-vps",
            "intent_id": "intent-1",
            free_text_key: "arbitrary free text that must never be re-emitted",
        },
    )
    config = VpsExecutionStatusApiConfig(runtime_id="vps-runtime-1")
    repository = FakeExecutionStatusRepository(status=_status(recent_events=(event,)))

    response = handle_vps_execution_status_request(
        "GET", config=config, repository=repository, now=NOW
    )

    payload = response.body["recent_events"][0]["payload"]
    assert payload is not None
    assert free_text_key not in payload
    assert "arbitrary free text" not in str(response.body)


def test_unexpected_field_on_the_status_view_is_never_emitted() -> None:
    """Deny-by-default: only allowlisted keys ever appear, regardless of read-model content."""
    config = VpsExecutionStatusApiConfig(runtime_id="vps-runtime-1")
    repository = FakeExecutionStatusRepository(status=_status())

    response = handle_vps_execution_status_request(
        "GET", config=config, repository=repository, now=NOW
    )

    allowed_keys = {
        "schema_version",
        "generated_at",
        "simulated",
        "runtime_id",
        "mode",
        "provider",
        "symbol",
        "status",
        "last_heartbeat_at",
        "last_market_event_at",
        "feed_connection_state",
        "feed_reconnect_count",
        "feed_last_error_code",
        "stale",
        "last_price",
        "recent_bars",
        "paper_equity",
        "realized_pnl",
        "unrealized_pnl",
        "current_position",
        "current_signal",
        "recent_orders",
        "recent_fills",
        "recent_events",
    }
    assert set(response.body.keys()) <= allowed_keys
    # Categorically forbidden content never appears anywhere in the body, even nested.
    forbidden_markers = ("state.json", "/state/", "AWS_REGION", "EXECUTION_STATE_TABLE", "s3://")
    for marker in forbidden_markers:
        assert marker not in str(response.body)


def test_restart_identity_fields_added_for_incompatible_state_detection_never_leak() -> None:
    """``account_id``/``currency``/``starting_equity`` exist on ``RuntimeStatusView`` only to let
    the worker refuse an incompatible restart (ADR-0036 section 4.4); they are restart-identity
    fields, not public status fields, and must never appear in the public response.
    """
    config = VpsExecutionStatusApiConfig(runtime_id="vps-runtime-1")
    repository = FakeExecutionStatusRepository(
        status=_status(
            account_id="paper-account-1",
            currency="USDT",
            starting_equity=Decimal("10000"),
        )
    )

    response = handle_vps_execution_status_request(
        "GET", config=config, repository=repository, now=NOW
    )

    assert "account_id" not in response.body
    assert "currency" not in response.body
    assert "starting_equity" not in response.body
    assert "paper-account-1" not in str(response.body)


def test_allowlist_covers_every_field_the_dashboard_http_datasource_reads() -> None:
    """Schema-compatibility guard (SPRINT_062.md T006): a future accidental narrowing of the v1
    allowlist should fail *here*, not be discovered later as a silently blank dashboard field.

    ``apps/dashboard`` is a separate Python environment (ADR-0022 rule 2 forbids it importing
    ``trading_framework``), so this cannot import the dashboard package directly. Instead it
    hard-codes the exact key set the two known consumers read, as of this writing:

    - ``dashboard_app.datasources.live_paper_http._summary_from_snapshot``: ``runtime_id``,
      ``symbol``, ``status``, ``last_heartbeat_at``, ``generated_at``, ``mode``.
    - ``dashboard_app.views.live_paper.live_paper_health`` /
      ``dashboard_app.views.live_paper.build_dry_run_status_card`` /
      ``dashboard_app.views.dry_run_status_card``: ``last_heartbeat_at``, ``status``, ``stale``,
      ``simulated``, ``feed_connection_state``, ``feed_reconnect_count``, ``feed_last_error``
      (deliberately absent from v1 -- see below), ``symbol``, ``current_position``,
      ``paper_equity``, ``realized_pnl``, ``unrealized_pnl``, ``recent_bars``, ``recent_fills``,
      ``recent_events``.

    If a dashboard change starts reading a new top-level key, update this set *and* confirm the
    key is genuinely in the v1 allowlist (or add it there deliberately, per ADR-0036 SS3.8).
    """
    dashboard_read_keys = {
        "runtime_id",
        "symbol",
        "status",
        "last_heartbeat_at",
        "generated_at",
        "mode",
        "stale",
        "simulated",
        "feed_connection_state",
        "feed_reconnect_count",
        "current_position",
        "paper_equity",
        "realized_pnl",
        "unrealized_pnl",
        "recent_bars",
        "recent_fills",
        "recent_events",
    }
    # `feed_last_error` is a deliberate ADR-0036 SS3.4 narrowing (replaced by
    # `feed_last_error_code`): the dashboard tolerates its absence via `.get(...)`, so it is
    # excluded from the required set rather than asserted present.

    config = VpsExecutionStatusApiConfig(runtime_id="vps-runtime-1")
    repository = FakeExecutionStatusRepository(status=_status())

    response = handle_vps_execution_status_request(
        "GET", config=config, repository=repository, now=NOW
    )

    missing = dashboard_read_keys - set(response.body.keys())
    assert not missing, f"dashboard-read fields missing from the v1 response: {missing}"


def test_health_check_reports_healthy_when_no_state_exists() -> None:
    config = VpsExecutionStatusApiConfig(runtime_id="vps-runtime-1")
    repository = FakeExecutionStatusRepository(status=None)

    response = handle_vps_status_health_check(repository=repository, config=config)

    assert response.status_code == 200
    assert response.body["status"] == "ok"
    assert response.body["state_volume_readable"] is True
    assert response.body["schema_version"] == SCHEMA_VERSION
    assert response.body["simulated"] is True


def test_health_check_reports_unreadable_state_volume_but_stays_200() -> None:
    config = VpsExecutionStatusApiConfig(runtime_id="vps-runtime-1")
    repository = FakeExecutionStatusRepository(status=None, error=OSError("volume unavailable"))

    response = handle_vps_status_health_check(repository=repository, config=config)

    assert response.status_code == 200
    assert response.body["state_volume_readable"] is False


def test_health_check_is_independent_of_worker_running_state() -> None:
    config = VpsExecutionStatusApiConfig(runtime_id="vps-runtime-1")
    running = FakeExecutionStatusRepository(status=_status())
    stopped = FakeExecutionStatusRepository(status=_status(status=RuntimeHealth.STOPPED))
    absent = FakeExecutionStatusRepository(status=None)

    for repository in (running, stopped, absent):
        response = handle_vps_status_health_check(repository=repository, config=config)
        assert response.status_code == 200


def test_load_config_requires_no_aws_specific_env_values() -> None:
    config = load_vps_execution_status_api_config({})

    assert config.runtime_id
    assert config.stale_after_seconds > 0


def test_response_body_is_fully_json_serializable() -> None:
    import json

    config = VpsExecutionStatusApiConfig(runtime_id="vps-runtime-1")
    repository = FakeExecutionStatusRepository(status=_status())

    response = handle_vps_execution_status_request(
        "GET", config=config, repository=repository, now=NOW
    )

    serialized = json.dumps(dict(response.body), sort_keys=True)
    assert json.loads(serialized) == response.body
