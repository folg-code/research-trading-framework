"""Tests for profile context."""

from trading_framework.core.profiling import active_phase_timer, optional_phase
from trading_framework.infrastructure.observability.phase_timer import PhaseTimer
from trading_framework.infrastructure.observability.profile_context import phase_timer_context


def test_phase_timer_context_installs_active_timer() -> None:
    timer = PhaseTimer(enabled=True)
    assert active_phase_timer() is None
    with phase_timer_context(timer):
        assert active_phase_timer() is timer
    assert active_phase_timer() is None


def test_optional_phase_records_when_timer_active() -> None:
    timer = PhaseTimer(enabled=True)
    with phase_timer_context(timer), optional_phase("child.phase"):
        pass
    assert "child.phase" in timer._stats
    assert timer._stats["child.phase"].call_count == 1


def test_optional_phase_is_noop_without_timer() -> None:
    with optional_phase("ignored.phase"):
        pass
