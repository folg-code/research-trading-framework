"""Read-only VPS execution status API: transport-independent request handling.

Implements the ``execution.status.v1`` public contract frozen in
``docs/adr/ADR-0035-vps-dry-run-runtime-and-status-boundary.md`` section 3. This module never
imports an HTTP framework: it only builds a versioned, allowlisted response from
``ExecutionStateReader``. Transport wiring (aiohttp, WSGI, etc.) lives in ``scripts/execution``.

Deny-by-default is structural, not a review checklist: this module only ever reads named
attributes off the typed read-model dataclasses (``RuntimeStatusView`` and friends), which
``JsonExecutionStateRepository`` already parses from the persisted document. Any unexpected key in
the raw JSON document is dropped by that parsing step and never reaches an attribute here, so it
can never be re-serialized into the public response.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Final, final

from trading_framework.core.exceptions import (
    ConfigurationError,
    TradingFrameworkError,
    ValidationError,
)
from trading_framework.core.types import Price
from trading_framework.execution import (
    DEFAULT_RECENT_BAR_LIMIT,
    DEFAULT_RECENT_EVENT_LIMIT,
    DEFAULT_RECENT_FILL_LIMIT,
    DEFAULT_RECENT_ORDER_LIMIT,
    ExecutionReadModelQuery,
    ExecutionStateReader,
    RecentBarView,
    RecentExecutionEventView,
    RecentFillView,
    RecentOrderView,
    RuntimeStatusView,
)
from trading_framework.execution.models import PaperPosition

SCHEMA_VERSION: Final = "execution.status.v1"
DEFAULT_RUNTIME_ID: Final = "btc-futures-dry-run-vps"
DEFAULT_STALE_AFTER_SECONDS: Final = 120
_ALLOWED_METHODS: Final = ("GET", "HEAD")
_RESPONSE_HEADERS: Final[Mapping[str, str]] = {
    "Content-Type": "application/json",
    "Cache-Control": "no-store",
}
_UNREADABLE_STATE_ERRORS: Final = (
    TradingFrameworkError,
    ValidationError,
    ValueError,
    KeyError,
    TypeError,
    OSError,
)

# Allowlisted `ExecutionEvent.payload` keys (ADR-0035 section 3.2/3.3). `payload` is a free-form
# `Mapping[str, str]` (`trading_framework.execution.models.events.ExecutionEvent.payload`); unlike
# the rest of this module, allowlisting the *field* "recent_events" is not enough, because the
# *value* of "payload" within it is operator/exception-adjacent free text unless each key is
# individually vetted. Every payload key actually emitted by `LocalExecutionRuntimeSession`
# (`execution/runtime/session.py`) is enumerated below as either safe (closed vocabulary, an id, an
# enum value, or a numeric value formatted as a string) or deliberately omitted. `message`,
# `reason` and `feed_last_error` are free text that can carry raw exception text or embed a stream
# URL/host -- the same category ADR-0035 section 3.4 closed for the top-level `feed_last_error`
# field (e.g. `RUNTIME_FAILED`'s `message`, built from `str(exc)[:500]` in
# `binance_local_btc_futures.py`, and persisted verbatim by `LocalExecutionRuntimeSession.fail`) --
# and are never emitted, truncated or otherwise transformed here. A key not in this set, including
# any future payload key this module does not yet know about, is silently dropped, never passed
# through.
_SAFE_EVENT_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(
    {
        "runtime_id",
        "provider",
        "status",
        "simulated",
        "event_at",
        "current_signal",
        "feed_connection_state",
        "feed_reconnect_count",
        "intent_id",
        "strategy_id",
        "side",
        "order_type",
        "quantity",
        "order_id",
        "fill_id",
        "price",
        "unrealized_pnl",
        "equity",
    }
)

# Closed vocabulary for feed_last_error_code. The raw feed_last_error string is never passed
# through: it can embed a stream URL or host (ADR-0035 section 3.4). Keyword matching is
# best-effort classification for operators; anything unmatched maps to "unknown", not omitted,
# so the dashboard can still show that a feed error occurred without seeing raw text.
_FEED_ERROR_KEYWORDS: Final[tuple[tuple[str, str], ...]] = (
    ("timed out", "connect_timeout"),
    ("timeout", "connect_timeout"),
    ("refused", "connect_timeout"),
    ("closed", "connection_closed"),
    ("reset", "connection_closed"),
    ("disconnect", "connection_closed"),
    ("protocol", "protocol_error"),
    ("handshake", "protocol_error"),
    ("decode", "protocol_error"),
)


@final
@dataclass(frozen=True, slots=True)
class VpsExecutionStatusApiConfig:
    """Read-only VPS status API configuration."""

    runtime_id: str = DEFAULT_RUNTIME_ID
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS
    recent_event_limit: int = DEFAULT_RECENT_EVENT_LIMIT
    recent_order_limit: int = DEFAULT_RECENT_ORDER_LIMIT
    recent_fill_limit: int = DEFAULT_RECENT_FILL_LIMIT
    recent_bar_limit: int = DEFAULT_RECENT_BAR_LIMIT

    def __post_init__(self) -> None:
        if not self.runtime_id.strip():
            raise ConfigurationError("TRADING_FRAMEWORK_STATUS_RUNTIME_ID must be non-empty")
        _require_positive(self.stale_after_seconds, "TRADING_FRAMEWORK_STATUS_STALE_AFTER_SECONDS")
        _require_positive(self.recent_event_limit, "TRADING_FRAMEWORK_STATUS_RECENT_EVENTS")
        _require_positive(self.recent_order_limit, "TRADING_FRAMEWORK_STATUS_RECENT_ORDERS")
        _require_positive(self.recent_fill_limit, "TRADING_FRAMEWORK_STATUS_RECENT_FILLS")
        _require_positive(self.recent_bar_limit, "TRADING_FRAMEWORK_STATUS_RECENT_BARS")

    @property
    def query(self) -> ExecutionReadModelQuery:
        """Read-model query bounds derived from this configuration."""
        return ExecutionReadModelQuery(
            runtime_id=self.runtime_id,
            recent_event_limit=self.recent_event_limit,
            recent_order_limit=self.recent_order_limit,
            recent_fill_limit=self.recent_fill_limit,
            recent_bar_limit=self.recent_bar_limit,
        )


def load_vps_execution_status_api_config(env: Mapping[str, str]) -> VpsExecutionStatusApiConfig:
    """Load the read-only VPS status API configuration from environment variables.

    No AWS-specific value is required (D062-02 / ADR-0035 section 6).
    """
    return VpsExecutionStatusApiConfig(
        runtime_id=_optional(env, "STATUS_RUNTIME_ID", DEFAULT_RUNTIME_ID),
        stale_after_seconds=_int(env, "STATUS_STALE_AFTER_SECONDS", DEFAULT_STALE_AFTER_SECONDS),
        recent_event_limit=_int(env, "STATUS_RECENT_EVENTS", DEFAULT_RECENT_EVENT_LIMIT),
        recent_order_limit=_int(env, "STATUS_RECENT_ORDERS", DEFAULT_RECENT_ORDER_LIMIT),
        recent_fill_limit=_int(env, "STATUS_RECENT_FILLS", DEFAULT_RECENT_FILL_LIMIT),
        recent_bar_limit=_int(env, "STATUS_RECENT_BARS", DEFAULT_RECENT_BAR_LIMIT),
    )


@final
@dataclass(frozen=True, slots=True)
class StatusApiResponse:
    """Transport-independent HTTP response for the status/health endpoints."""

    status_code: int
    headers: Mapping[str, str]
    body: Mapping[str, Any]


def handle_vps_execution_status_request(
    method: str,
    *,
    config: VpsExecutionStatusApiConfig,
    repository: ExecutionStateReader,
    now: datetime,
) -> StatusApiResponse:
    """Handle one GET-only request against the ``execution.status.v1`` contract."""
    normalized_method = method.upper()
    if normalized_method not in _ALLOWED_METHODS:
        return _error_response(
            405,
            error="method_not_allowed",
            message="only GET is supported",
            now=now,
            extra_headers={"Allow": "GET"},
        )
    try:
        view = repository.latest_status_view(config.query)
    except _UNREADABLE_STATE_ERRORS:
        return _error_response(
            503,
            error="status_unavailable",
            message="execution state is unreadable",
            now=now,
        )
    if view is None:
        return _error_response(
            404,
            error="runtime_status_not_found",
            message="no execution state for the configured runtime",
            now=now,
            runtime_id=config.runtime_id,
        )
    stale = (now - view.last_heartbeat_at) > timedelta(seconds=config.stale_after_seconds)
    body = _status_body(view, generated_at=now, stale=stale)
    return StatusApiResponse(status_code=200, headers=_RESPONSE_HEADERS, body=body)


def handle_vps_status_health_check(
    *,
    repository: ExecutionStateReader,
    config: VpsExecutionStatusApiConfig,
) -> StatusApiResponse:
    """Report process liveness and state-volume readability only (ADR-0035 section 4.5).

    Always returns 200: the fact this handler ran proves the process is alive. A missing runtime
    (``latest_status_view`` returning ``None``) is healthy — the worker may simply be stopped.
    Only an unreadable/corrupt state volume flips ``state_volume_readable`` to ``False``; it does
    not by itself make the health check fail.
    """
    readable = True
    try:
        repository.latest_status_view(config.query)
    except _UNREADABLE_STATE_ERRORS:
        readable = False
    body = {
        "schema_version": SCHEMA_VERSION,
        "simulated": True,
        "status": "ok",
        "state_volume_readable": readable,
    }
    return StatusApiResponse(status_code=200, headers=_RESPONSE_HEADERS, body=body)


def _status_body(view: RuntimeStatusView, *, generated_at: datetime, stale: bool) -> dict[str, Any]:
    return {
        # Envelope
        "schema_version": SCHEMA_VERSION,
        "generated_at": _datetime_to_json(generated_at),
        "simulated": True,
        # Identity
        "runtime_id": view.runtime_id,
        "mode": view.mode.value,
        "provider": view.provider,
        "symbol": view.symbol,
        # Health
        "status": view.status.value,
        "last_heartbeat_at": _datetime_to_json(view.last_heartbeat_at),
        "last_market_event_at": _optional_datetime_to_json(view.last_market_event_at),
        "feed_connection_state": view.feed_connection_state,
        "feed_reconnect_count": view.feed_reconnect_count,
        "feed_last_error_code": _feed_last_error_code(view.feed_last_error),
        "stale": stale,
        # Market
        "last_price": _optional_price_to_json(view.last_price),
        "recent_bars": [_bar_to_json(bar) for bar in view.recent_bars],
        # Paper account
        "paper_equity": _optional_decimal_to_json(view.paper_equity),
        "realized_pnl": _optional_decimal_to_json(view.realized_pnl),
        "unrealized_pnl": _optional_decimal_to_json(view.unrealized_pnl),
        # Paper position
        "current_position": _position_to_json(view.current_position),
        "current_signal": view.current_signal,
        # Bounded activity
        "recent_orders": [_order_to_json(order) for order in view.recent_orders],
        "recent_fills": [_fill_to_json(fill) for fill in view.recent_fills],
        "recent_events": [_event_to_json(event) for event in view.recent_events],
    }


def _feed_last_error_code(feed_last_error: str | None) -> str | None:
    if feed_last_error is None:
        return None
    lowered = feed_last_error.lower()
    for keyword, code in _FEED_ERROR_KEYWORDS:
        if keyword in lowered:
            return code
    return "unknown"


def _error_response(
    status_code: int,
    *,
    error: str,
    message: str,
    now: datetime,
    extra_headers: Mapping[str, str] | None = None,
    **extra_fields: Any,
) -> StatusApiResponse:
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _datetime_to_json(now),
        "simulated": True,
        "error": error,
        "message": message,
    }
    body.update(extra_fields)
    headers = dict(_RESPONSE_HEADERS)
    if extra_headers is not None:
        headers.update(extra_headers)
    return StatusApiResponse(status_code=status_code, headers=headers, body=body)


def _order_to_json(order: RecentOrderView) -> dict[str, Any]:
    return {
        "order_id": order.order_id,
        "intent_id": order.intent_id,
        "strategy_id": order.strategy_id,
        "symbol": order.symbol,
        "side": order.side.value,
        "order_type": order.order_type.value,
        "quantity": _decimal_to_json(order.quantity),
        "status": order.status.value,
        "created_at": _datetime_to_json(order.created_at),
        "simulated": order.simulated,
    }


def _fill_to_json(fill: RecentFillView) -> dict[str, Any]:
    return {
        "fill_id": fill.fill_id,
        "order_id": fill.order_id,
        "symbol": fill.symbol,
        "side": fill.side.value,
        "quantity": _decimal_to_json(fill.quantity),
        "price": fill.price.to_json(),
        "filled_at": _datetime_to_json(fill.filled_at),
        "liquidity": fill.liquidity,
        "simulated": fill.simulated,
    }


def _event_to_json(event: RecentExecutionEventView) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "occurred_at": _datetime_to_json(event.occurred_at),
        "symbol": event.symbol,
        "payload": _sanitized_event_payload(event.payload),
        "correlation_id": event.correlation_id,
        "simulated": event.simulated,
    }


def _sanitized_event_payload(payload: Mapping[str, str] | None) -> dict[str, str] | None:
    """Allowlist ``ExecutionEvent.payload`` keys; see ``_SAFE_EVENT_PAYLOAD_KEYS`` above.

    Never passes through free text (``message``, ``reason``, ``feed_last_error``) or any
    unrecognized key -- deny by default, structurally, not by review.
    """
    if payload is None:
        return None
    return {key: value for key, value in payload.items() if key in _SAFE_EVENT_PAYLOAD_KEYS}


def _bar_to_json(bar: RecentBarView) -> dict[str, Any]:
    return {
        "open": bar.open.to_json(),
        "high": bar.high.to_json(),
        "low": bar.low.to_json(),
        "close": bar.close.to_json(),
        "volume": bar.volume.to_json(),
        "observed_at": _datetime_to_json(bar.observed_at),
        "available_at": _datetime_to_json(bar.available_at),
        "simulated": bar.simulated,
    }


def _position_to_json(position: PaperPosition | None) -> dict[str, Any] | None:
    if position is None:
        return None
    return {
        "symbol": position.symbol,
        "side": position.side.value,
        "quantity": _decimal_to_json(position.quantity),
        "average_entry_price": _optional_price_to_json(position.average_entry_price),
        "mark_price": _optional_price_to_json(position.mark_price),
        "unrealized_pnl": _decimal_to_json(position.unrealized_pnl),
        "updated_at": _datetime_to_json(position.updated_at),
        "simulated": position.simulated,
    }


def _datetime_to_json(value: datetime) -> str:
    return value.isoformat()


def _optional_datetime_to_json(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _decimal_to_json(value: Decimal) -> str:
    return format(value, "f")


def _optional_decimal_to_json(value: Decimal | None) -> str | None:
    return _decimal_to_json(value) if value is not None else None


def _optional_price_to_json(value: Price | None) -> str | None:
    return value.to_json() if value is not None else None


def _optional(env: Mapping[str, str], name: str, default: str) -> str:
    value = env.get(f"TRADING_FRAMEWORK_{name}")
    if value is None or not value.strip():
        return default
    return value


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = _optional(env, name, str(default))
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"TRADING_FRAMEWORK_{name} must be an integer") from exc


def _require_positive(value: int, field_name: str) -> None:
    if value < 1:
        raise ConfigurationError(f"{field_name} must be positive")
