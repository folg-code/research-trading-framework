"""Temporal alignment policy contracts."""

from enum import StrEnum


class AlignmentPolicy(StrEnum):
    """Policy for aligning higher-timeframe outputs to an evaluation grid."""

    LAST_CLOSED_BAR = "last_closed_bar"
    INTRABAR = "intrabar"
