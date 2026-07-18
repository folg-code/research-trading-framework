"""AWS dry-run datasource contract stub (no HTTP client in Sprint 028)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dashboard_app.contracts import RunSummary


@runtime_checkable
class AwsDryRunDataSource(Protocol):
    """Future dry-run datasource contract (Sprint 028: stub only — no HTTP client)."""

    def list_live_sessions(self) -> tuple[RunSummary, ...]:
        """Return dry-run session summaries exposed by a future AWS status API."""

    def fetch_session_snapshot(self, session_id: str) -> dict[str, object]:
        """Return one dry-run session snapshot payload."""


class UnimplementedAwsDryRunDataSource:
    """Placeholder AWS dry-run datasource — raises until a later sprint wires HTTP."""

    def list_live_sessions(self) -> tuple[RunSummary, ...]:
        msg = "AwsDryRunDataSource is not implemented in Sprint 028 (contracts only)"
        raise NotImplementedError(msg)

    def fetch_session_snapshot(self, session_id: str) -> dict[str, object]:
        del session_id
        msg = "AwsDryRunDataSource is not implemented in Sprint 028 (contracts only)"
        raise NotImplementedError(msg)
