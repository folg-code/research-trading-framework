"""Compare persisted Predictive Research runs on one dataset fingerprint."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.estimators import EstimatorSpec
from trading_framework.research.predictive.leaderboard import (
    LeaderboardRunSnapshot,
    PredictiveLeaderboard,
    build_predictive_leaderboard,
    primary_metric_for_task,
)


@dataclass(frozen=True, slots=True)
class ComparePredictiveRunsRequest:
    """Input for one single-study Predictive Research leaderboard."""

    run_dirs: tuple[Path, ...]
    output_path: Path | None = None


@dataclass(frozen=True, slots=True)
class ComparePredictiveRunsResult:
    """Leaderboard plus the path it was written to."""

    leaderboard: PredictiveLeaderboard
    output_path: Path


def compare_predictive_runs(request: ComparePredictiveRunsRequest) -> ComparePredictiveRunsResult:
    """Load run directories, rank pooled primary scores, write ``leaderboard.json``.

    Default output is ``leaderboard.json`` next to the first run directory.
    Mismatched dataset fingerprints raise ``PredictiveSpecError``.
    """
    if not request.run_dirs:
        msg = "compare_predictive_runs requires at least one run directory"
        raise PredictiveSpecError(msg)
    snapshots = tuple(_snapshot_from_run_dir(Path(path)) for path in request.run_dirs)
    leaderboard = build_predictive_leaderboard(snapshots)
    output_path = (
        Path(request.output_path)
        if request.output_path is not None
        else Path(request.run_dirs[0]) / "leaderboard.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(leaderboard.to_dict(), indent=2), encoding="utf-8")
    return ComparePredictiveRunsResult(leaderboard=leaderboard, output_path=output_path)


def _snapshot_from_run_dir(run_dir: Path) -> LeaderboardRunSnapshot:
    manifest_path = run_dir / "manifest.json"
    metrics_path = run_dir / "metrics.json"
    if not manifest_path.is_file():
        msg = f"run directory is missing manifest.json: {run_dir}"
        raise PredictiveSpecError(msg)
    if not metrics_path.is_file():
        msg = f"run directory is missing metrics.json: {run_dir}"
        raise PredictiveSpecError(msg)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"run directory contains invalid JSON: {run_dir}"
        raise PredictiveSpecError(msg) from exc
    if not isinstance(manifest, Mapping) or not isinstance(metrics, Mapping):
        msg = f"run directory JSON must be objects: {run_dir}"
        raise PredictiveSpecError(msg)
    try:
        spec = EstimatorSpec.from_dict(manifest["estimator_spec"])
        run_id = str(manifest["run_id"])
        dataset_fingerprint = str(manifest["dataset_fingerprint"])
        library = str(manifest["library"])
        library_version = str(manifest["library_version"])
    except (KeyError, TypeError, ValidationError, PredictiveSpecError) as exc:
        msg = f"run manifest is missing required identity fields: {run_dir}"
        raise PredictiveSpecError(msg) from exc
    metric = primary_metric_for_task(spec.task_type).value
    return LeaderboardRunSnapshot(
        run_id=run_id,
        dataset_fingerprint=dataset_fingerprint,
        task_type=spec.task_type,
        family=spec.family,
        library=library,
        library_version=library_version,
        pooled_primary_by_source=_pooled_primary_by_source(metrics, metric=metric),
    )


def _pooled_primary_by_source(
    metrics: Mapping[str, Any],
    *,
    metric: str,
) -> dict[str, float | None]:
    pooled = metrics.get("pooled")
    if not isinstance(pooled, Mapping):
        msg = "metrics payload must include a pooled mapping"
        raise PredictiveSpecError(msg)
    scores: dict[str, float | None] = {}
    for source, raw in pooled.items():
        if not isinstance(raw, Mapping):
            msg = f"pooled[{source!r}] must be a mapping"
            raise PredictiveSpecError(msg)
        statistical = raw.get("statistical")
        if not isinstance(statistical, Mapping):
            msg = f"pooled[{source!r}] must include statistical scores"
            raise PredictiveSpecError(msg)
        scores[str(source)] = _optional_number(statistical.get(metric), field_name=metric)
    return scores


def _optional_number(value: object, *, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{field_name} must be a number or null"
        raise PredictiveSpecError(msg)
    number = float(value)
    if not math.isfinite(number):
        return None
    return number
