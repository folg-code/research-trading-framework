"""Single-study Predictive Research leaderboard (D-S042-13).

Library-free ranking over persisted run snapshots. Not a model registry
(TD-021). Cross-study comparison spanning dataset fingerprints is out of
scope.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.estimators import TaskType
from trading_framework.research.predictive.metrics import MetricSource
from trading_framework.research.predictive.selection import SelectionMetric

_BASELINE_SOURCES = frozenset(
    {
        MetricSource.CONSTANT_MEAN.value,
        MetricSource.MAJORITY_CLASS.value,
        MetricSource.RANDOM_PERMUTATION.value,
    }
)


class LeaderboardRowKind(StrEnum):
    """Whether a row is a fitted estimator or a metric-layer baseline."""

    ESTIMATOR = "ESTIMATOR"
    BASELINE = "BASELINE"


@dataclass(frozen=True, slots=True)
class LeaderboardRunSnapshot:
    """One persisted run's identity plus pooled primary scores by source."""

    run_id: str
    dataset_fingerprint: str
    task_type: TaskType
    family: str
    library: str
    library_version: str
    pooled_primary_by_source: Mapping[str, float | None]


@dataclass(frozen=True, slots=True)
class LeaderboardRow:
    """One ranked estimator or baseline entry."""

    rank: int
    kind: LeaderboardRowKind
    run_id: str
    family: str
    source: str
    pooled_primary: float | None
    metric: str
    library: str
    library_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "kind": self.kind.value,
            "run_id": self.run_id,
            "family": self.family,
            "source": self.source,
            "pooled_primary": self.pooled_primary,
            "metric": self.metric,
            "library": self.library,
            "library_version": self.library_version,
        }


@dataclass(frozen=True, slots=True)
class PredictiveLeaderboard:
    """Ranked comparison of runs that share one dataset fingerprint."""

    dataset_fingerprint: str
    metric: str
    task_type: TaskType
    rows: tuple[LeaderboardRow, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_fingerprint": self.dataset_fingerprint,
            "metric": self.metric,
            "task_type": self.task_type.value,
            "rows": [row.to_dict() for row in self.rows],
        }


def primary_metric_for_task(task_type: TaskType) -> SelectionMetric:
    """Return the D-S042-11 / D-S042-13 ranking metric for ``task_type``."""
    if task_type is TaskType.CLASSIFICATION:
        return SelectionMetric.ROC_AUC
    return SelectionMetric.SPEARMAN_IC


def build_predictive_leaderboard(
    snapshots: Sequence[LeaderboardRunSnapshot],
) -> PredictiveLeaderboard:
    """Rank estimator MODEL rows and present S040 baselines as extra rows."""
    if not snapshots:
        msg = "leaderboard requires at least one run"
        raise PredictiveSpecError(msg)
    fingerprints = {item.dataset_fingerprint for item in snapshots}
    if len(fingerprints) != 1:
        msg = f"leaderboard runs must share one dataset fingerprint; got {sorted(fingerprints)}"
        raise PredictiveSpecError(msg)
    task_types = {item.task_type for item in snapshots}
    if len(task_types) != 1:
        msg = (
            "leaderboard runs must share one task_type; "
            f"got {sorted(item.value for item in task_types)}"
        )
        raise PredictiveSpecError(msg)
    task_type = next(iter(task_types))
    metric = primary_metric_for_task(task_type).value
    unranked: list[tuple[float | None, LeaderboardRow]] = []
    for snapshot in snapshots:
        if MetricSource.MODEL.value not in snapshot.pooled_primary_by_source:
            msg = f"run {snapshot.run_id!r} metrics are missing pooled MODEL scores"
            raise PredictiveSpecError(msg)
        unranked.append(
            (
                snapshot.pooled_primary_by_source[MetricSource.MODEL.value],
                LeaderboardRow(
                    rank=0,
                    kind=LeaderboardRowKind.ESTIMATOR,
                    run_id=snapshot.run_id,
                    family=snapshot.family,
                    source=MetricSource.MODEL.value,
                    pooled_primary=snapshot.pooled_primary_by_source[MetricSource.MODEL.value],
                    metric=metric,
                    library=snapshot.library,
                    library_version=snapshot.library_version,
                ),
            )
        )
        for source, score in snapshot.pooled_primary_by_source.items():
            if source not in _BASELINE_SOURCES:
                continue
            unranked.append(
                (
                    score,
                    LeaderboardRow(
                        rank=0,
                        kind=LeaderboardRowKind.BASELINE,
                        run_id=snapshot.run_id,
                        family=source,
                        source=source,
                        pooled_primary=score,
                        metric=metric,
                        library=snapshot.library,
                        library_version=snapshot.library_version,
                    ),
                )
            )
    ordered = sorted(unranked, key=_rank_key)
    rows = tuple(
        LeaderboardRow(
            rank=index,
            kind=row.kind,
            run_id=row.run_id,
            family=row.family,
            source=row.source,
            pooled_primary=row.pooled_primary,
            metric=row.metric,
            library=row.library,
            library_version=row.library_version,
        )
        for index, (_score, row) in enumerate(ordered, start=1)
    )
    return PredictiveLeaderboard(
        dataset_fingerprint=next(iter(fingerprints)),
        metric=metric,
        task_type=task_type,
        rows=rows,
    )


def _rank_key(item: tuple[float | None, LeaderboardRow]) -> tuple[int, float]:
    score, _row = item
    if score is None:
        return (1, 0.0)
    return (0, -score)
