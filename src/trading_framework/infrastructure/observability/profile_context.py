"""Thread-local active phase timer for deep profiling hooks."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from trading_framework.core import profiling as core_profiling
from trading_framework.core.profiling import optional_phase
from trading_framework.infrastructure.observability.phase_timer import PhaseTimer

__all__ = ["PhaseTimer", "active_phase_timer", "optional_phase", "phase_timer_context"]


def active_phase_timer() -> PhaseTimer | None:
    """Return the infrastructure timer installed by :func:`phase_timer_context`."""
    timer = core_profiling.active_phase_timer()
    if isinstance(timer, PhaseTimer):
        return timer
    return None


@contextmanager
def phase_timer_context(timer: PhaseTimer | None) -> Iterator[None]:
    """Install ``timer`` for nested profiling hooks."""
    if timer is None or not timer.enabled:
        yield
        return
    token = core_profiling._set_active_phase_timer(timer)
    try:
        yield
    finally:
        core_profiling._reset_active_phase_timer(token)
