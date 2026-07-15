"""Execution mode contracts."""

from enum import StrEnum


class ExecutionMode(StrEnum):
    """Supported execution modes."""

    DRY_RUN = "dry_run"


SUPPORTED_EXECUTION_MODES = frozenset({ExecutionMode.DRY_RUN})


def is_supported_execution_mode(mode: ExecutionMode) -> bool:
    """Return whether an execution mode is implemented in the current increment."""
    return mode in SUPPORTED_EXECUTION_MODES
