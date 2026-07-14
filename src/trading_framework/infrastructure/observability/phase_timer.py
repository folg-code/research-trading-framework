"""Lightweight phase timing for long-running preprocessing workflows."""

from __future__ import annotations

import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TextIO


@dataclass(slots=True)
class PhaseStats:
    """Aggregated timing for one named phase."""

    name: str
    inclusive_seconds: float = 0.0
    self_seconds: float = 0.0
    call_count: int = 0
    max_inclusive_seconds: float = 0.0

    def record(self, *, inclusive_seconds: float, self_seconds: float) -> None:
        self.inclusive_seconds += inclusive_seconds
        self.self_seconds += self_seconds
        self.call_count += 1
        if inclusive_seconds > self.max_inclusive_seconds:
            self.max_inclusive_seconds = inclusive_seconds

    @property
    def avg_inclusive_seconds(self) -> float:
        if self.call_count == 0:
            return 0.0
        return self.inclusive_seconds / self.call_count

    @property
    def avg_self_seconds(self) -> float:
        if self.call_count == 0:
            return 0.0
        return self.self_seconds / self.call_count


@dataclass(slots=True)
class _PhaseFrame:
    name: str
    started_at: float
    child_seconds: float = 0.0


@dataclass
class PhaseTimer:
    """Collect per-phase durations and emit human-readable reports."""

    enabled: bool = True
    log_stream: TextIO = field(default_factory=lambda: sys.stderr)
    _stats: dict[str, PhaseStats] = field(default_factory=dict)
    _stack: list[_PhaseFrame] = field(default_factory=list)
    _session_started_at: float | None = field(default=None, init=False)

    def begin_session(self) -> None:
        """Start wall-clock tracking for the next report."""
        if self.enabled:
            self._session_started_at = time.perf_counter()

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        """Time one block and aggregate inclusive/self durations under ``name``."""
        if not self.enabled:
            yield
            return
        started = time.perf_counter()
        frame = _PhaseFrame(name=name, started_at=started)
        self._stack.append(frame)
        try:
            yield
        finally:
            finished = time.perf_counter()
            current = self._stack.pop()
            inclusive = finished - current.started_at
            self_seconds = max(0.0, inclusive - current.child_seconds)
            stats = self._stats.get(name)
            if stats is None:
                stats = PhaseStats(name=name)
                self._stats[name] = stats
            stats.record(inclusive_seconds=inclusive, self_seconds=self_seconds)
            if self._stack:
                self._stack[-1].child_seconds += inclusive

    def log(self, message: str) -> None:
        """Write one progress line when profiling is enabled."""
        if self.enabled:
            print(message, file=self.log_stream, flush=True)

    def report(self, *, title: str = "Phase timing report", min_pct: float = 0.0) -> None:
        """Print sorted aggregate timings with inclusive and self columns."""
        if not self.enabled or not self._stats:
            return
        inclusive_total = sum(stats.inclusive_seconds for stats in self._stats.values())
        self_total = sum(stats.self_seconds for stats in self._stats.values())
        wall_clock_total = (
            time.perf_counter() - self._session_started_at
            if self._session_started_at is not None
            else inclusive_total
        )
        self.log(f"\n{title}")
        self.log(
            f"{'phase':<32} {'incl_s':>9} {'self_s':>9} {'calls':>7} "
            f"{'avg_incl':>9} {'max_incl':>9} {'self%':>7}"
        )
        for name in sorted(
            self._stats, key=lambda key: self._stats[key].self_seconds, reverse=True
        ):
            stats = self._stats[name]
            pct = 0.0 if wall_clock_total == 0 else (stats.self_seconds / wall_clock_total) * 100
            if pct < min_pct and stats.self_seconds < 0.01:
                continue
            self.log(
                f"{stats.name:<32} "
                f"{stats.inclusive_seconds:9.2f} "
                f"{stats.self_seconds:9.2f} "
                f"{stats.call_count:7d} "
                f"{stats.avg_inclusive_seconds:9.3f} "
                f"{stats.max_inclusive_seconds:9.3f} "
                f"{pct:6.1f}%"
            )
        self.log(f"{'SELF_TOTAL':<32} {'':>9} {self_total:9.2f}")
        self.log(f"{'INCLUSIVE_TOTAL':<32} {inclusive_total:9.2f}")
        self.log(f"{'WALL_CLOCK_TOTAL':<32} {wall_clock_total:9.2f}")
