"""Fold-contained sequence windows for Predictive Research (D-S043-09/10).

Library-free: polars, numpy, and framework contracts only. Application calls
the builder after fold assignment and before ``fit()`` / ``predict()``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import polars as pl

from trading_framework.research.predictive.errors import (
    PredictiveMatrixError,
    PredictiveSpecError,
)
from trading_framework.research.predictive.splitting import FoldRole
from trading_framework.time.models.utc_instant import require_utc_aware

MIN_LOOKBACK_BARS = 2
MAX_LOOKBACK_BARS = 256
MIN_EFFECTIVE_SAMPLE = 10
WINDOW_ACCOUNTING_FILENAME = "window_accounting.json"
WINDOW_ACCOUNTING_SCHEMA_VERSION = "window_accounting.v1"

_REQUIRED_COLUMNS = ("entity_id", "available_at", "fold_role")


class PaddingPolicy(StrEnum):
    """Incomplete-window policy. Only ``DROP`` is valid this sprint."""

    DROP = "DROP"


@dataclass(frozen=True, slots=True)
class SequenceWindowSpec:
    """Lookback window identity hashed into a predictive run (D-S043-09).

    ``lookback_bars`` counts the end row. Incomplete windows are dropped,
    never padded.
    """

    lookback_bars: int
    stride: int = 1
    padding_policy: PaddingPolicy = PaddingPolicy.DROP

    def __post_init__(self) -> None:
        if isinstance(self.lookback_bars, bool) or not isinstance(self.lookback_bars, int):
            msg = "lookback_bars must be an integer"
            raise PredictiveSpecError(msg)
        if not (MIN_LOOKBACK_BARS <= self.lookback_bars <= MAX_LOOKBACK_BARS):
            msg = (
                f"lookback_bars must be in [{MIN_LOOKBACK_BARS}, {MAX_LOOKBACK_BARS}], "
                f"got {self.lookback_bars}"
            )
            raise PredictiveSpecError(msg)
        if isinstance(self.stride, bool) or not isinstance(self.stride, int) or self.stride < 1:
            msg = "stride must be a positive integer"
            raise PredictiveSpecError(msg)

    def identity_payload(self) -> dict[str, Any]:
        """Canonical mapping hashed into run identity."""
        return self.to_dict()

    def to_dict(self) -> dict[str, Any]:
        return {
            "lookback_bars": self.lookback_bars,
            "stride": self.stride,
            "padding_policy": self.padding_policy.value,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SequenceWindowSpec:
        try:
            lookback_bars = payload["lookback_bars"]
        except KeyError as exc:
            msg = f"sequence window spec missing field: {exc.args[0]}"
            raise PredictiveSpecError(msg) from exc
        raw_policy = payload.get("padding_policy", PaddingPolicy.DROP.value)
        try:
            padding_policy = PaddingPolicy(str(raw_policy))
        except ValueError as exc:
            msg = f"padding_policy must be DROP, got {raw_policy!r}"
            raise PredictiveSpecError(msg) from exc
        return cls(
            lookback_bars=_require_int(lookback_bars, field_name="lookback_bars"),
            stride=_require_int(payload.get("stride", 1), field_name="stride"),
            padding_policy=padding_policy,
        )


@dataclass(frozen=True, slots=True)
class RoleWindowAccounting:
    """Dropped-window counts for one fold role (D-S043-10)."""

    fold_id: int
    fold_role: FoldRole
    candidate_end_rows: int
    windows_built: int
    windows_dropped_incomplete: int
    windows_dropped_gap: int
    windows_dropped_fold_boundary: int

    def __post_init__(self) -> None:
        if self.fold_role not in (FoldRole.TRAIN, FoldRole.TEST):
            msg = f"window accounting fold_role must be TRAIN or TEST, got {self.fold_role.value}"
            raise PredictiveSpecError(msg)
        counted = (
            self.windows_built
            + self.windows_dropped_incomplete
            + self.windows_dropped_gap
            + self.windows_dropped_fold_boundary
        )
        if counted != self.candidate_end_rows:
            msg = (
                "window accounting counts must sum to candidate_end_rows: "
                f"built={self.windows_built} incomplete={self.windows_dropped_incomplete} "
                f"gap={self.windows_dropped_gap} boundary={self.windows_dropped_fold_boundary} "
                f"candidates={self.candidate_end_rows}"
            )
            raise PredictiveSpecError(msg)

    @property
    def effective_sample(self) -> int:
        return self.windows_built

    def to_dict(self) -> dict[str, Any]:
        return {
            "fold_id": self.fold_id,
            "fold_role": self.fold_role.value,
            "candidate_end_rows": self.candidate_end_rows,
            "windows_built": self.windows_built,
            "windows_dropped_incomplete": self.windows_dropped_incomplete,
            "windows_dropped_gap": self.windows_dropped_gap,
            "windows_dropped_fold_boundary": self.windows_dropped_fold_boundary,
            "effective_sample": self.effective_sample,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RoleWindowAccounting:
        try:
            fold_role = FoldRole(str(payload["fold_role"]))
        except (KeyError, ValueError) as exc:
            msg = f"invalid window accounting fold_role: {payload.get('fold_role')!r}"
            raise PredictiveSpecError(msg) from exc
        return cls(
            fold_id=_require_int(payload.get("fold_id"), field_name="fold_id"),
            fold_role=fold_role,
            candidate_end_rows=_require_int(
                payload.get("candidate_end_rows"), field_name="candidate_end_rows"
            ),
            windows_built=_require_int(payload.get("windows_built"), field_name="windows_built"),
            windows_dropped_incomplete=_require_int(
                payload.get("windows_dropped_incomplete"),
                field_name="windows_dropped_incomplete",
            ),
            windows_dropped_gap=_require_int(
                payload.get("windows_dropped_gap"), field_name="windows_dropped_gap"
            ),
            windows_dropped_fold_boundary=_require_int(
                payload.get("windows_dropped_fold_boundary"),
                field_name="windows_dropped_fold_boundary",
            ),
        )


@dataclass(frozen=True, slots=True)
class WindowAccounting:
    """Sidecar payload written as ``window_accounting.json`` (D-S043-10)."""

    entries: tuple[RoleWindowAccounting, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": WINDOW_ACCOUNTING_SCHEMA_VERSION,
            "folds": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> WindowAccounting:
        raw_entries = payload.get("folds")
        if not isinstance(raw_entries, Sequence) or isinstance(raw_entries, (str, bytes)):
            msg = "window accounting folds must be a sequence"
            raise PredictiveSpecError(msg)
        return cls(entries=tuple(RoleWindowAccounting.from_dict(item) for item in raw_entries))


@dataclass(frozen=True, slots=True)
class SequenceWindows:
    """Rank-3 feature windows plus the accounting for one builder call."""

    features: npt.NDArray[np.float64]
    target: npt.NDArray[np.float64]
    end_available_at: tuple[datetime, ...]
    end_entity_ids: tuple[str, ...]
    accounting: RoleWindowAccounting

    def __post_init__(self) -> None:
        if self.features.ndim != 3:
            msg = "sequence window features must be rank-3 (n_windows, lookback, n_features)"
            raise PredictiveSpecError(msg)
        n_windows = int(self.features.shape[0])
        if self.target.shape != (n_windows,):
            msg = "sequence window target length must match the number of windows"
            raise PredictiveSpecError(msg)
        if len(self.end_available_at) != n_windows or len(self.end_entity_ids) != n_windows:
            msg = "sequence window end metadata length must match the number of windows"
            raise PredictiveSpecError(msg)


def build_sequence_windows(
    rows: pl.DataFrame,
    *,
    spec: SequenceWindowSpec,
    feature_columns: Sequence[str],
    bar_duration: timedelta,
    fold_role: FoldRole,
    fold_id: int,
    target_column: str = "label",
) -> SequenceWindows:
    """Build fold-contained windows ending on ``fold_role`` rows (D-S043-09).

    Pass the full fold frame (all roles for one ``fold_id``). Filtering to
    TRAIN/TEST first would hide purge rows as adjacent TRAIN samples.
    """
    if fold_role not in (FoldRole.TRAIN, FoldRole.TEST):
        msg = f"sequence windows fold_role must be TRAIN or TEST, got {fold_role.value}"
        raise PredictiveSpecError(msg)
    if bar_duration <= timedelta(0):
        msg = "bar_duration must be a positive duration"
        raise PredictiveSpecError(msg)
    aliases = tuple(str(column) for column in feature_columns)
    if not aliases:
        msg = "sequence windows require at least one feature column"
        raise PredictiveSpecError(msg)
    fold_rows = _fold_rows(rows, fold_id=fold_id)
    _require_columns(fold_rows, (*_REQUIRED_COLUMNS, *aliases, target_column))

    features: list[npt.NDArray[np.float64]] = []
    targets: list[float] = []
    end_available_at: list[datetime] = []
    end_entity_ids: list[str] = []
    dropped_incomplete = 0
    dropped_gap = 0
    dropped_boundary = 0
    candidate_end_rows = 0

    for entity_rows in _iter_entity_groups(fold_rows):
        roles = [_parse_role(value) for value in entity_rows.get_column("fold_role").to_list()]
        stamps = [
            _aware_timestamp(value) for value in entity_rows.get_column("available_at").to_list()
        ]
        feature_matrix = entity_rows.select(aliases).to_numpy()
        labels = entity_rows.get_column(target_column).to_list()
        entity_id = str(entity_rows.get_column("entity_id").to_list()[0])
        candidate_indices = [index for index, role in enumerate(roles) if role is fold_role]
        attempted = candidate_indices[:: spec.stride]
        candidate_end_rows += len(attempted)
        for end_index in attempted:
            start_index = end_index - spec.lookback_bars + 1
            if start_index < 0:
                dropped_incomplete += 1
                continue
            window_roles = roles[start_index : end_index + 1]
            if any(role is not fold_role for role in window_roles):
                dropped_boundary += 1
                continue
            window_stamps = stamps[start_index : end_index + 1]
            if _has_gap(window_stamps, bar_duration=bar_duration):
                dropped_gap += 1
                continue
            window = np.asarray(feature_matrix[start_index : end_index + 1], dtype=np.float64)
            features.append(window)
            targets.append(float(labels[end_index]))
            end_available_at.append(stamps[end_index])
            end_entity_ids.append(entity_id)

    accounting = RoleWindowAccounting(
        fold_id=fold_id,
        fold_role=fold_role,
        candidate_end_rows=candidate_end_rows,
        windows_built=len(features),
        windows_dropped_incomplete=dropped_incomplete,
        windows_dropped_gap=dropped_gap,
        windows_dropped_fold_boundary=dropped_boundary,
    )
    stacked = (
        np.stack(features, axis=0)
        if features
        else np.empty((0, spec.lookback_bars, len(aliases)), dtype=np.float64)
    )
    return SequenceWindows(
        features=stacked,
        target=np.asarray(targets, dtype=np.float64),
        end_available_at=tuple(end_available_at),
        end_entity_ids=tuple(end_entity_ids),
        accounting=accounting,
    )


def require_min_effective_sample(
    accounting: RoleWindowAccounting,
    *,
    minimum: int = MIN_EFFECTIVE_SAMPLE,
) -> None:
    """Reject a fold role whose surviving windows are too few to score (D-S043-10)."""
    if minimum < 1:
        msg = "minimum effective sample must be at least 1"
        raise PredictiveSpecError(msg)
    if accounting.effective_sample < minimum:
        msg = (
            f"fold {accounting.fold_id} {accounting.fold_role.value} effective_sample "
            f"{accounting.effective_sample} is below {minimum} after windowing"
        )
        raise PredictiveSpecError(msg)


def write_window_accounting(path: Path, accounting: WindowAccounting) -> None:
    """Persist ``window_accounting.json`` next to a predictive run."""
    path.write_text(json.dumps(accounting.to_dict(), indent=2) + "\n", encoding="utf-8")


def read_window_accounting(path: Path) -> WindowAccounting:
    """Load a ``window_accounting.json`` sidecar."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        msg = "window accounting file must contain a mapping"
        raise PredictiveSpecError(msg)
    return WindowAccounting.from_dict(payload)


def _fold_rows(rows: pl.DataFrame, *, fold_id: int) -> pl.DataFrame:
    if "fold_id" not in rows.columns:
        return rows
    return rows.filter(pl.col("fold_id") == fold_id)


def _require_columns(rows: pl.DataFrame, required: tuple[str, ...]) -> None:
    missing = [name for name in required if name not in rows.columns]
    if missing:
        msg = f"missing required column: {missing[0]}"
        raise PredictiveMatrixError(msg)


def _iter_entity_groups(rows: pl.DataFrame) -> tuple[pl.DataFrame, ...]:
    if rows.height == 0:
        return ()
    ordered = rows.sort(["entity_id", "available_at"])
    groups: list[pl.DataFrame] = []
    for entity_id in ordered.get_column("entity_id").unique(maintain_order=True).to_list():
        groups.append(ordered.filter(pl.col("entity_id") == entity_id))
    return tuple(groups)


def _parse_role(value: object) -> FoldRole:
    if isinstance(value, FoldRole):
        return value
    try:
        return FoldRole(str(value))
    except ValueError as exc:
        msg = f"invalid fold_role: {value!r}"
        raise PredictiveSpecError(msg) from exc


def _aware_timestamp(value: object) -> datetime:
    if not isinstance(value, datetime):
        msg = "available_at must be a datetime"
        raise PredictiveMatrixError(msg)
    return require_utc_aware(value)


def _has_gap(stamps: Sequence[datetime], *, bar_duration: timedelta) -> bool:
    return any(current - previous > bar_duration for previous, current in pairwise(stamps))


def _require_int(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field_name} must be an integer"
        raise PredictiveSpecError(msg)
    return value
