"""Thread-local active phase timer for deep profiling hooks."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from trading_framework.infrastructure.observability.phase_timer import PhaseTimer

_active_timer: ContextVar[PhaseTimer | None] = ContextVar("active_phase_timer", default=None)


def active_phase_timer() -> PhaseTimer | None:
    """Return the timer installed by :func:`phase_timer_context`, if any."""
    return _active_timer.get()


@contextmanager
def phase_timer_context(timer: PhaseTimer | None) -> Iterator[None]:
    """Install ``timer`` for nested infrastructure profiling hooks."""
    if timer is None or not timer.enabled:
        yield
        return
    token = _active_timer.set(timer)
    try:
        yield
    finally:
        _active_timer.reset(token)
