"""Live Paper presentation helpers (read-only status payload)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import plotly.graph_objects as go

DEFAULT_STALE_AFTER = timedelta(minutes=3)

_STATUS_BADGES = {
    "running": "Running",
    "active": "Running",
    "ok": "Running",
    "degraded": "Degraded",
    "stale": "Stale",
    "stopped": "Stopped",
    "idle": "Stopped",
    "failed": "Failed",
    "error": "Failed",
}

_PUBLIC_STATUS_SCALARS = frozenset(
    {
        "status",
        "simulated",
        "last_heartbeat_at",
        "feed_connection_state",
        "feed_reconnect_count",
        "symbol",
        "current_signal",
        "last_price",
        "last_market_event_at",
        "paper_equity",
        "realized_pnl",
        "unrealized_pnl",
    }
)
_PUBLIC_POSITION_FIELDS = frozenset(
    {
        "side",
        "position",
        "quantity",
        "qty",
        "size",
        "entry_price",
        "avg_entry_price",
        "mark_price",
        "unrealized_pnl",
    }
)
_PUBLIC_BAR_FIELDS = frozenset({"observed_at", "open", "high", "low", "close"})
_PUBLIC_FILL_FIELDS = frozenset({"filled_at", "event_at", "price", "fill_price", "side"})


@dataclass(frozen=True, slots=True)
class LivePaperHealth:
    """Derived health flags for one status snapshot."""

    simulated: bool
    heartbeat_at: datetime | None
    is_stale: bool
    stale_after: timedelta
    badge: str
    status: str
    feed_connection_state: str | None = None
    feed_reconnect_count: int = 0
    feed_last_error: str | None = None


def sanitize_public_live_paper_snapshot(snapshot: Mapping[str, object]) -> dict[str, object]:
    """Return the fixed public subset of a runtime status response.

    Unknown fields, raw events, orders, trades and error details are omitted.
    The public page can therefore never acquire a new field merely because the
    private status API adds one.
    """
    public = {key: snapshot[key] for key in _PUBLIC_STATUS_SCALARS if key in snapshot}
    position = snapshot.get("current_position")
    if isinstance(position, Mapping):
        public["current_position"] = {
            key: position[key] for key in _PUBLIC_POSITION_FIELDS if key in position
        }
    bars = _allowlisted_rows(snapshot.get("recent_bars"), _PUBLIC_BAR_FIELDS, limit=300)
    if bars:
        public["recent_bars"] = bars
    fills = _allowlisted_rows(snapshot.get("recent_fills"), _PUBLIC_FILL_FIELDS, limit=100)
    if fills:
        public["recent_fills"] = fills
    return public


def _allowlisted_rows(
    value: object,
    allowed_fields: frozenset[str],
    *,
    limit: int,
) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows = [
        {key: item[key] for key in allowed_fields if key in item}
        for item in value[-limit:]
        if isinstance(item, Mapping)
    ]
    return [row for row in rows if row]


def parse_utc_datetime(value: object) -> datetime | None:
    """Parse an ISO-8601 timestamp into UTC, or return None."""
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def live_paper_health(
    snapshot: Mapping[str, object],
    *,
    now: datetime | None = None,
    stale_after: timedelta = DEFAULT_STALE_AFTER,
) -> LivePaperHealth:
    """Derive badge/health flags from a status API snapshot."""
    heartbeat = parse_utc_datetime(snapshot.get("last_heartbeat_at"))
    clock = now or datetime.now(UTC)
    clock = clock.replace(tzinfo=UTC) if clock.tzinfo is None else clock.astimezone(UTC)
    heartbeat_stale = heartbeat is None or (clock - heartbeat) > stale_after
    status_raw = str(snapshot.get("status") or "unknown").strip().lower()
    if heartbeat_stale and status_raw in {"running", "degraded", "active", "ok"}:
        badge = "Stale"
        effective_status = "stale"
    else:
        badge = _STATUS_BADGES.get(status_raw, status_raw.title() or "Unknown")
        effective_status = status_raw

    reconnect_raw = snapshot.get("feed_reconnect_count", 0)
    try:
        reconnect_count = (
            int(reconnect_raw)
            if isinstance(reconnect_raw, (str, bytes, bytearray, int, float))
            else 0
        )
    except (TypeError, ValueError):
        reconnect_count = 0
    feed_state = snapshot.get("feed_connection_state")
    feed_error = snapshot.get("feed_last_error")
    return LivePaperHealth(
        simulated=snapshot.get("simulated") is True,
        heartbeat_at=heartbeat,
        is_stale=badge == "Stale" or effective_status == "stale",
        stale_after=stale_after,
        badge=badge,
        status=effective_status,
        feed_connection_state=str(feed_state) if isinstance(feed_state, str) else None,
        feed_reconnect_count=max(reconnect_count, 0),
        feed_last_error=str(feed_error) if isinstance(feed_error, str) and feed_error else None,
    )


#: The honest state vocabulary the home-page dry-run card must distinguish
#: (SPRINT_062.md T005 acceptance criteria): a fresh snapshot is ``current``;
#: an explicitly stale one (``stale: true`` or a heartbeat older than the
#: threshold) is ``stale``; a worker-reported ``FAILED`` status is ``failed``;
#: an unreachable status API is ``offline``; ``404`` (no runtime started/wiped)
#: is ``not_found``; any other error (e.g. ``503``) is ``unavailable``; and an
#: unconfigured ``DASHBOARD_STATUS_URL`` is ``not_configured`` -- the card must
#: never render as if it were ``current`` under any other state.
DryRunCardKind = Literal[
    "not_configured",
    "offline",
    "not_found",
    "unavailable",
    "failed",
    "stale",
    "current",
]


#: The closed vocabulary ADR-0036 SS3.2 allows for the `status` field. Any
#: other value (including a missing field) is treated as an untrustworthy
#: response, not as an implicit "current" state.
_RECOGNIZED_STATUSES = frozenset({"running", "degraded", "stale", "stopped", "failed"})


@dataclass(frozen=True, slots=True)
class DryRunStatusCard:
    """Presentation state for the home-page BTC dry-run status card."""

    kind: DryRunCardKind
    health: LivePaperHealth | None = None
    snapshot: Mapping[str, object] | None = None
    detail: str | None = None


def build_dry_run_status_card(
    *,
    status_url: str | None,
    snapshot: Mapping[str, object] | None,
    error: str | None,
    now: datetime | None = None,
    stale_after: timedelta = DEFAULT_STALE_AFTER,
) -> DryRunStatusCard:
    """Classify a status API call's outcome into an honest card state.

    ``error`` is the ``str(ValueError)`` raised by
    :class:`~dashboard_app.datasources.live_paper_http.HttpLivePaperStatusDataSource`
    (never both ``error`` and ``snapshot`` set). This never presents an old
    snapshot as current: callers pass the snapshot from the *current* call
    only, never a cached one from a prior successful call.
    """
    if status_url is None or not status_url.strip():
        return DryRunStatusCard(kind="not_configured")
    if error is not None:
        lowered = error.lower()
        if "http 404" in lowered:
            return DryRunStatusCard(kind="not_found", detail=error)
        if "unreachable" in lowered:
            return DryRunStatusCard(kind="offline", detail=error)
        return DryRunStatusCard(kind="unavailable", detail=error)
    if snapshot is None:
        return DryRunStatusCard(kind="offline", detail="status API returned no data")

    status_raw = str(snapshot.get("status") or "").strip().lower()
    if status_raw not in _RECOGNIZED_STATUSES:
        # A missing/unrecognized `status` (ADR-0036 SS3.2's closed vocabulary:
        # RUNNING/DEGRADED/STALE/STOPPED/FAILED) means the response cannot be
        # trusted as a health signal. Never fall through to "current" here --
        # that would silently present an unhealthy/malformed payload as good.
        raw_value = snapshot.get("status")
        detail = f"status API response has a missing or unrecognized `status` value: {raw_value!r}"
        return DryRunStatusCard(kind="unavailable", detail=detail)

    health = live_paper_health(snapshot, now=now, stale_after=stale_after)
    if status_raw == "failed":
        return DryRunStatusCard(kind="failed", health=health, snapshot=snapshot)
    if status_raw == "stale":
        return DryRunStatusCard(kind="stale", health=health, snapshot=snapshot)
    is_stale = bool(snapshot.get("stale")) or health.is_stale
    return DryRunStatusCard(
        kind="stale" if is_stale else "current",
        health=health,
        snapshot=snapshot,
    )


def build_live_paper_candles(recent_bars: object) -> go.Figure:
    """Build a candlestick figure from status ``recent_bars`` payload rows."""
    figure = go.Figure()
    rows = _bar_rows(recent_bars)
    if not rows:
        figure.update_layout(
            title="No recent bars in status snapshot",
            height=360,
            margin={"l": 40, "r": 20, "t": 40, "b": 30},
        )
        return figure
    figure.add_trace(
        go.Candlestick(
            x=[row["observed_at"] for row in rows],
            open=[row["open"] for row in rows],
            high=[row["high"] for row in rows],
            low=[row["low"] for row in rows],
            close=[row["close"] for row in rows],
            name="OHLCV",
        )
    )
    figure.update_layout(
        height=420,
        margin={"l": 40, "r": 20, "t": 20, "b": 30},
        xaxis_rangeslider_visible=False,
        showlegend=False,
    )
    return figure


def fill_marker_points(recent_fills: object) -> tuple[list[datetime], list[float], list[str]]:
    """Extract scatter marker series from status ``recent_fills`` rows."""
    if not isinstance(recent_fills, list):
        return [], [], []
    xs: list[datetime] = []
    ys: list[float] = []
    texts: list[str] = []
    for row in recent_fills:
        if not isinstance(row, Mapping):
            continue
        filled_at = parse_utc_datetime(row.get("filled_at") or row.get("event_at"))
        price = _as_float(row.get("price") or row.get("fill_price"))
        if filled_at is None or price is None:
            continue
        side = str(row.get("side") or "fill")
        xs.append(filled_at)
        ys.append(price)
        texts.append(side)
    return xs, ys, texts


def attach_fill_markers(figure: go.Figure, recent_fills: object) -> go.Figure:
    """Overlay simulated fill markers on a candlestick figure."""
    xs, ys, texts = fill_marker_points(recent_fills)
    if not xs:
        return figure
    figure.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers+text",
            name="fills",
            text=texts,
            textposition="top center",
            marker={"size": 10, "symbol": "diamond", "color": "#d62728"},
        )
    )
    return figure


def _bar_rows(recent_bars: object) -> list[dict[str, Any]]:
    if not isinstance(recent_bars, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in recent_bars:
        if not isinstance(item, Mapping):
            continue
        observed = parse_utc_datetime(item.get("observed_at"))
        open_ = _as_float(item.get("open"))
        high = _as_float(item.get("high"))
        low = _as_float(item.get("low"))
        close = _as_float(item.get("close"))
        if observed is None or None in (open_, high, low, close):
            continue
        rows.append(
            {
                "observed_at": observed,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
            }
        )
    rows.sort(key=lambda row: row["observed_at"])
    return rows


def _as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return None
    return None


def event_timeline_rows(recent_events: object) -> Sequence[dict[str, object]]:
    """Normalize recent events for a compact timeline table."""
    if not isinstance(recent_events, list):
        return ()
    rows: list[dict[str, object]] = []
    for item in recent_events:
        if not isinstance(item, Mapping):
            continue
        rows.append(
            {
                "event_at": item.get("event_at") or item.get("occurred_at"),
                "event_type": item.get("event_type") or item.get("type"),
                "message": item.get("message") or item.get("current_signal"),
            }
        )
    return tuple(rows)
