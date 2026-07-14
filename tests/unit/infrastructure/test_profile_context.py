"""Tests for profile context."""

from trading_framework.infrastructure.observability.phase_timer import PhaseTimer
from trading_framework.infrastructure.observability.profile_context import (
    active_phase_timer,
    phase_timer_context,
)


def test_phase_timer_context_installs_active_timer() -> None:
    timer = PhaseTimer(enabled=True)
    assert active_phase_timer() is None
    with phase_timer_context(timer):
        assert active_phase_timer() is timer
    assert active_phase_timer() is None
