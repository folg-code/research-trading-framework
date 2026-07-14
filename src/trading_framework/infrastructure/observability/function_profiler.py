"""cProfile helpers for function-level bottleneck reports."""

from __future__ import annotations

import cProfile
import pstats
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from io import StringIO
from typing import TextIO


@dataclass(frozen=True, slots=True)
class FunctionProfileReport:
    """Top functions ranked by cumulative time."""

    title: str
    total_seconds: float
    lines: tuple[str, ...]


@dataclass
class FunctionProfiler:
    """Collect and render function-level timing via :mod:`cProfile`."""

    enabled: bool = True
    log_stream: TextIO = sys.stderr

    def __post_init__(self) -> None:
        self._profiler = cProfile.Profile() if self.enabled else None

    @contextmanager
    def session(self) -> Iterator[None]:
        """Profile one code block."""
        if self._profiler is None:
            yield
            return
        self._profiler.enable()
        try:
            yield
        finally:
            self._profiler.disable()

    def report(
        self,
        *,
        title: str = "Function profile report",
        top_n: int = 40,
        path_prefix: str | None = None,
    ) -> FunctionProfileReport:
        """Render top functions sorted by cumulative time."""
        if self._profiler is None:
            return FunctionProfileReport(title=title, total_seconds=0.0, lines=())

        stream = StringIO()
        stats = pstats.Stats(self._profiler, stream=stream)
        stats.strip_dirs()
        stats.sort_stats(pstats.SortKey.CUMULATIVE)
        stats.print_stats(top_n)

        raw_lines = [line.rstrip() for line in stream.getvalue().splitlines()]
        total_seconds = _extract_total_seconds(raw_lines)

        print(f"\n{title}", file=self.log_stream, flush=True)
        for line in raw_lines:
            print(line, file=self.log_stream, flush=True)
        if path_prefix:
            print(f"\n{title} (filtered: {path_prefix})", file=self.log_stream, flush=True)
            for line in raw_lines:
                normalized = line.replace("\\", "/")
                if path_prefix.replace("\\", "/") in normalized:
                    print(line, file=self.log_stream, flush=True)
        if total_seconds > 0:
            print(f"profiled_total_s: {total_seconds:.2f}", file=self.log_stream, flush=True)

        return FunctionProfileReport(
            title=title,
            total_seconds=total_seconds,
            lines=tuple(raw_lines),
        )


def _extract_total_seconds(lines: list[str]) -> float:
    for line in lines:
        if "function calls" in line and "seconds" in line:
            parts = line.split()
            for index, part in enumerate(parts):
                if part == "seconds" and index > 0:
                    try:
                        return float(parts[index - 1])
                    except ValueError:
                        return 0.0
    return 0.0
