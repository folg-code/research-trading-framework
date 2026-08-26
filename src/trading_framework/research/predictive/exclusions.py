"""Exclusion counts for labelled Predictive Research feature-matrix rows."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MatrixExclusionCounts:
    """How candidate evaluation-bar rows were kept or dropped.

    Each candidate row is counted once. Incomplete and insufficient outcome
    statuses take precedence over null features, so a trailing bar with a
    missing feature is ``incomplete_horizon``, not ``null_features``.
    """

    candidate_rows: int
    labelled_rows: int
    incomplete_horizon: int
    insufficient_data: int
    null_features: int
