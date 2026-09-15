"""Windows process-tree termination and reconciliation primitives (Sprint 064 T007).

Pure `ctypes` against `kernel32.dll` -- no new third-party dependency
(D-S064-03's explicit constraint: a process-tree kill that needs a new
dependency is a STOP-AND-REPORT, not an in-sprint addition; the maintainer's
platform is Windows, and this module is exercised only there -- CI runs on
`ubuntu-latest`, see the module's own test file for how that's handled).

Graceful termination reuses Python's own `CTRL_BREAK_EVENT` support
(`Popen.send_signal`, available once the child is spawned with
`CREATE_NEW_PROCESS_GROUP`) -- stdlib already covers it, no ctypes needed.
Only two things stdlib does not expose at all:

1. **Hard-kill the whole tree.** `Process.kill()` calls `TerminateProcess`
   on just the root pid; it does not touch a grandchild `uv run` spawns
   (ADR-0041 section 3's open sub-question). A Windows Job Object assigned
   right after spawn lets one `TerminateJobObject` call kill every process
   in the tree at once. The job object is created WITHOUT
   `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`: closing our handle to it (including
   this process exiting) must never auto-kill the child -- ADR-0041's own
   rationale is "a crash... kills the job, not the control API", and section
   5's restart reconciliation only makes sense if a still-running child can
   survive a `workbench-api` restart.
2. **A process's creation time**, needed for pid/start-time reconciliation
   after a restart (ADR-0041 section 5): a bare pid is not enough to tell
   "still our job" from "the OS recycled this pid for something else".
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

IS_WINDOWS = sys.platform == "win32"

_PROCESS_TERMINATE = 0x0001
_PROCESS_SET_QUOTA = 0x0100
_PROCESS_QUERY_INFORMATION = 0x0400
_JOB_ASSIGN_ACCESS = _PROCESS_TERMINATE | _PROCESS_SET_QUOTA | _PROCESS_QUERY_INFORMATION

# pragma: no cover - the else branch is exercised only off the maintainer's Windows machine
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True) if IS_WINDOWS else None


class WindowsProcessError(RuntimeError):
    """Raised when a Win32 call needed for process-tree management fails."""


def _require_windows() -> ctypes.WinDLL:
    """Return the loaded `kernel32`, narrowing it away from `WinDLL | None`
    for every call site below -- `_kernel32` is only `None` on non-Windows,
    where this raises instead."""
    if not IS_WINDOWS or _kernel32 is None:
        raise WindowsProcessError("windows_process is only usable on win32")
    return _kernel32


def create_job_object() -> int:
    """Create an unnamed Job Object with no auto-kill-on-close limit."""
    kernel32 = _require_windows()
    handle = kernel32.CreateJobObjectW(None, None)
    if not handle:
        raise WindowsProcessError(f"CreateJobObjectW failed: {ctypes.get_last_error()}")
    return int(handle)


def assign_process_to_job(job_handle: int, pid: int) -> None:
    """Add the process named by `pid` (and, once spawned, its descendants
    inherit job membership too) to the job at `job_handle`."""
    kernel32 = _require_windows()
    process_handle = kernel32.OpenProcess(_JOB_ASSIGN_ACCESS, False, pid)
    if not process_handle:
        raise WindowsProcessError(f"OpenProcess({pid}) failed: {ctypes.get_last_error()}")
    try:
        if not kernel32.AssignProcessToJobObject(job_handle, process_handle):
            raise WindowsProcessError(
                f"AssignProcessToJobObject({pid}) failed: {ctypes.get_last_error()}"
            )
    finally:
        kernel32.CloseHandle(process_handle)


def terminate_job_object(job_handle: int, exit_code: int = 1) -> None:
    """Kill every process currently in the job, in one call."""
    kernel32 = _require_windows()
    if not kernel32.TerminateJobObject(job_handle, exit_code):
        raise WindowsProcessError(f"TerminateJobObject failed: {ctypes.get_last_error()}")


def close_handle(handle: int) -> None:
    kernel32 = _require_windows()
    kernel32.CloseHandle(handle)


_STILL_ACTIVE = 259


def process_creation_time(pid: int) -> int | None:
    """The process's creation time as an opaque, comparable integer (the raw
    100ns-tick FILETIME `GetProcessTimes` reports), or `None` if `pid` is not
    currently running.

    A terminated Windows process stays queryable by pid -- `OpenProcess` and
    `GetProcessTimes` both keep succeeding -- for as long as any handle to it
    is still open (e.g. its own parent hasn't reaped it yet), so this also
    checks `GetExitCodeProcess` for `STILL_ACTIVE`; without that check a
    just-killed process would misreport as alive.
    """
    kernel32 = _require_windows()
    process_handle = kernel32.OpenProcess(_JOB_ASSIGN_ACCESS, False, pid)
    if not process_handle:
        return None
    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(process_handle, ctypes.byref(exit_code)):
            return None
        if exit_code.value != _STILL_ACTIVE:
            return None

        creation = wintypes.FILETIME()
        exit_time = wintypes.FILETIME()
        kernel_time = wintypes.FILETIME()
        user_time = wintypes.FILETIME()
        ok = kernel32.GetProcessTimes(
            process_handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel_time),
            ctypes.byref(user_time),
        )
        if not ok:
            return None
        return (creation.dwHighDateTime << 32) | creation.dwLowDateTime
    finally:
        kernel32.CloseHandle(process_handle)


def is_process_alive(pid: int) -> bool:
    return process_creation_time(pid) is not None
