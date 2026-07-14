"""Optional phase hooks for deep profiling without infrastructure coupling."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Protocol


class SupportsPhaseTiming(Protocol):
    """Minimal timer surface used by :func:`optional_phase`."""

    enabled: bool

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        """Time one named block."""
        ...


_active_timer: ContextVar[SupportsPhaseTiming | None] = ContextVar(
    "active_phase_timer",
    default=None,
)


def active_phase_timer() -> SupportsPhaseTiming | None:
    """Return the timer installed by application profiling context, if any."""
    return _active_timer.get()


def _set_active_phase_timer(timer: SupportsPhaseTiming | None) -> Token[SupportsPhaseTiming | None]:
    return _active_timer.set(timer)


def _reset_active_phase_timer(token: Token[SupportsPhaseTiming | None]) -> None:
    _active_timer.reset(token)


@contextmanager
def optional_phase(name: str) -> Iterator[None]:
    """Record one named phase when a parent timer is active."""
    timer = active_phase_timer()
    if timer is None:
        yield
        return
    with timer.phase(name):
        yield
