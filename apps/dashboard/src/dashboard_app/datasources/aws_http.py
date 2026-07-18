"""HTTP GET client for the read-only AWS dry-run status API."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, final
from urllib.parse import urlparse

from dashboard_app.contracts import PRESENTATION_SCHEMA_VERSION, RunSummary, WorkflowKind
from dashboard_app.datasources.aws_stub import AwsDryRunDataSource

DEFAULT_STATUS_TIMEOUT_SECONDS = 10.0
_Urlopener = Callable[[urllib.request.Request, float | None], Any]


@final
@dataclass(frozen=True, slots=True)
class HttpAwsDryRunDataSource:
    """Read-only AWS status API client (GET only — never mutates remote state)."""

    status_url: str
    timeout_seconds: float = DEFAULT_STATUS_TIMEOUT_SECONDS
    _urlopen: _Urlopener | None = None

    def __post_init__(self) -> None:
        url = self.status_url.strip()
        if not url:
            msg = "status_url must be a non-empty HTTP(S) URL"
            raise ValueError(msg)
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            msg = "status_url must be an absolute http or https URL"
            raise ValueError(msg)
        if self.timeout_seconds <= 0:
            msg = "timeout_seconds must be positive"
            raise ValueError(msg)
        object.__setattr__(self, "status_url", url)

    def list_live_sessions(self) -> tuple[RunSummary, ...]:
        """Return a single catalog row derived from the status snapshot."""
        snapshot = self.fetch_session_snapshot("")
        return (_summary_from_snapshot(snapshot),)

    def fetch_session_snapshot(self, session_id: str) -> dict[str, object]:
        """GET the status URL and return the JSON object body.

        ``session_id`` is ignored: the status Lambda serves one configured
        runtime. The parameter remains for :class:`AwsDryRunDataSource` parity.
        """
        del session_id
        payload = self._get_json()
        if not isinstance(payload, dict):
            msg = "status API response must be a JSON object"
            raise ValueError(msg)
        return dict(payload)

    def _get_json(self) -> object:
        request = urllib.request.Request(
            self.status_url,
            method="GET",
            headers={"Accept": "application/json"},
        )
        opener = self._urlopen or urllib.request.urlopen
        try:
            with opener(request, timeout=self.timeout_seconds) as response:
                status = int(getattr(response, "status", 200))
                body = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            msg = f"status API HTTP {exc.code}: {detail[:200]}"
            raise ValueError(msg) from exc
        except urllib.error.URLError as exc:
            msg = f"status API unreachable: {exc.reason}"
            raise ValueError(msg) from exc
        if status >= 400:
            msg = f"status API HTTP {status}"
            raise ValueError(msg)
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            msg = "status API response is not valid JSON"
            raise ValueError(msg) from exc


def _summary_from_snapshot(snapshot: dict[str, object]) -> RunSummary:
    runtime_id = str(snapshot.get("runtime_id") or "unknown-runtime")
    symbol = snapshot.get("symbol")
    status = snapshot.get("status")
    title_parts = ["Live paper"]
    if isinstance(symbol, str) and symbol.strip():
        title_parts.append(symbol.strip())
    if isinstance(status, str) and status.strip():
        title_parts.append(status.strip())
    created_at = _parse_optional_datetime(
        snapshot.get("last_heartbeat_at") or snapshot.get("generated_at")
    )
    return RunSummary(
        schema_version=PRESENTATION_SCHEMA_VERSION,
        workflow=WorkflowKind.LIVE_PAPER,
        run_id=runtime_id,
        created_at_utc=created_at,
        title=" · ".join(title_parts),
        storage_path=str(snapshot.get("mode") or "aws-status-api"),
        source_dataset_ref=str(symbol) if isinstance(symbol, str) else None,
        evaluation_timeframe="1m",
        research_scope="live_paper",
    )


def _parse_optional_datetime(value: object) -> datetime | None:
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


def assert_implements_protocol(source: HttpAwsDryRunDataSource) -> AwsDryRunDataSource:
    """Type helper for tests — ensures structural Protocol match."""
    return source
