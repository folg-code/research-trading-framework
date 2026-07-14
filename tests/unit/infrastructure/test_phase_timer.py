"""Tests for phase timing helper."""

import pytest

from trading_framework.infrastructure.observability.phase_timer import PhaseTimer


def test_phase_timer_aggregates_durations(capsys: pytest.CaptureFixture[str]) -> None:
    timer = PhaseTimer(enabled=True)
    timer.begin_session()
    with timer.phase("decode"):
        pass
    with timer.phase("decode"):
        pass
    with timer.phase("write"):
        pass
    timer.report()

    captured = capsys.readouterr()
    assert "decode" in captured.err
    assert "write" in captured.err
    assert "WALL_CLOCK_TOTAL" in captured.err
    assert "SELF_TOTAL" in captured.err


def test_phase_timer_nested_phases_track_self_time(capsys: pytest.CaptureFixture[str]) -> None:
    timer = PhaseTimer(enabled=True)
    timer.begin_session()
    with timer.phase("outer"), timer.phase("inner"):
        pass
    timer.report()

    captured = capsys.readouterr()
    assert "outer" in captured.err
    assert "inner" in captured.err
    assert "self_s" in captured.err
