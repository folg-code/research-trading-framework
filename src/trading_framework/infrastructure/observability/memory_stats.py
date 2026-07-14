"""Process memory helpers for import observability."""

from __future__ import annotations

import sys


def process_rss_mb() -> float | None:
    """Return current resident set size in megabytes when available."""
    getter = _windows_working_set_mb if sys.platform == "win32" else _posix_rss_mb
    return getter()


def _windows_working_set_mb() -> float | None:
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return None

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(ProcessMemoryCounters)
    windll = getattr(ctypes, "windll", None)
    if windll is None:
        return None
    process_handle = windll.kernel32.GetCurrentProcess()
    if (
        windll.psapi.GetProcessMemoryInfo(
            process_handle,
            ctypes.byref(counters),
            counters.cb,
        )
        == 0
    ):
        return None
    return float(counters.WorkingSetSize) / (1024 * 1024)


def _posix_rss_mb() -> float | None:
    try:
        with open("/proc/self/status", encoding="utf-8") as status_file:
            for line in status_file:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return float(parts[1]) / 1024
    except OSError:
        return None
    return None
