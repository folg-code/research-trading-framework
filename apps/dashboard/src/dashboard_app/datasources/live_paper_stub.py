"""Live Paper status datasource contract + implementations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dashboard_app.contracts import RunSummary


@runtime_checkable
class LivePaperStatusDataSource(Protocol):
    """Read-only dry-run datasource (status API / future multi-runtime catalog)."""

    def list_live_sessions(self) -> tuple[RunSummary, ...]:
        """Return dry-run session summaries exposed by the status API."""

    def fetch_session_snapshot(self, session_id: str) -> dict[str, object]:
        """Return one dry-run session snapshot payload."""


class UnimplementedLivePaperStatusDataSource:
    """Placeholder dry-run datasource — raises until status URL is configured."""

    def list_live_sessions(self) -> tuple[RunSummary, ...]:
        msg = "LivePaperStatusDataSource requires DASHBOARD_STATUS_URL (or sidebar status URL)"
        raise NotImplementedError(msg)

    def fetch_session_snapshot(self, session_id: str) -> dict[str, object]:
        del session_id
        msg = "LivePaperStatusDataSource requires DASHBOARD_STATUS_URL (or sidebar status URL)"
        raise NotImplementedError(msg)
