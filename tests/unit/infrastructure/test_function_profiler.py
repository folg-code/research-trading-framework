"""Tests for function profiler."""

import pytest

from trading_framework.infrastructure.observability.function_profiler import FunctionProfiler


def test_function_profiler_collects_hot_path(capsys: pytest.CaptureFixture[str]) -> None:
    profiler = FunctionProfiler(enabled=True)

    def work() -> int:
        total = 0
        for value in range(10_000):
            total += value * value
        return total

    with profiler.session():
        work()

    report = profiler.report(title="test profile", top_n=5)

    assert report.total_seconds >= 0.0
    assert report.lines
    assert any("work" in line or "function calls" in line for line in report.lines)
