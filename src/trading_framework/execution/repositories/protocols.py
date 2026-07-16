"""Repository protocols for dry-run execution state."""

from __future__ import annotations

from typing import Protocol

from trading_framework.execution.models import (
    ExecutionEvent,
    PaperAccountSnapshot,
    PaperPosition,
    RuntimeStatusSnapshot,
    SimulatedFill,
    SimulatedOrder,
)
from trading_framework.execution.repositories.read_models import (
    ExecutionReadModelQuery,
    RecentBarView,
    RecentExecutionEventView,
    RuntimeStatusView,
)
from trading_framework.market.models import MarketBar


class ExecutionStateWriter(Protocol):
    """Write-side port for operational dry-run execution state."""

    def append_event(self, runtime_id: str, event: ExecutionEvent) -> None:
        """Persist one immutable execution event."""
        ...

    def save_runtime_status(self, status: RuntimeStatusSnapshot) -> None:
        """Persist the latest runtime status snapshot."""
        ...

    def save_order(self, runtime_id: str, order: SimulatedOrder) -> None:
        """Persist or update one simulated order read-model item."""
        ...

    def save_fill(self, runtime_id: str, fill: SimulatedFill) -> None:
        """Persist one simulated fill read-model item."""
        ...

    def save_position(self, runtime_id: str, position: PaperPosition) -> None:
        """Persist the latest paper position snapshot."""
        ...

    def save_account(self, runtime_id: str, account: PaperAccountSnapshot) -> None:
        """Persist the latest paper account snapshot."""
        ...

    def save_bar(self, runtime_id: str, bar: MarketBar) -> None:
        """Persist one recent closed market bar for dashboard history."""
        ...


class ExecutionStateReader(Protocol):
    """Read-only port for execution dashboards and public status APIs."""

    def latest_status_view(self, query: ExecutionReadModelQuery) -> RuntimeStatusView | None:
        """Return the latest dashboard-ready status view for one runtime."""
        ...

    def recent_events(self, query: ExecutionReadModelQuery) -> tuple[RecentExecutionEventView, ...]:
        """Return recent execution events for one runtime."""
        ...

    def recent_bars(self, query: ExecutionReadModelQuery) -> tuple[RecentBarView, ...]:
        """Return recent closed market bars for one runtime."""
        ...


class ExecutionStateRepository(ExecutionStateWriter, ExecutionStateReader, Protocol):
    """Combined execution state repository contract."""
