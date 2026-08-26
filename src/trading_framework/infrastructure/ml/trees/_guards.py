"""Library-free fit guards shared by tree adapters (D-S042-09 / D-S042-10)."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.preprocessing import require_train_only_fit_roles
from trading_framework.research.predictive.splitting import FoldRole


def as_target_vector(target: object, *, n_rows: int) -> np.ndarray:
    """Coerce ``target`` to a 1-d array aligned with the feature matrix."""
    array = np.squeeze(np.asarray(target))
    if array.ndim != 1:
        msg = "target must be 1-dimensional"
        raise PredictiveSpecError(msg)
    if array.shape[0] != n_rows:
        msg = f"target length {array.shape[0]} does not match feature rows {n_rows}"
        raise PredictiveSpecError(msg)
    if array.shape[0] == 0:
        msg = "target must be non-empty"
        raise PredictiveSpecError(msg)
    if np.issubdtype(array.dtype, np.number) and np.isnan(array.astype(np.float64)).any():
        msg = "target must not contain NaN"
        raise PredictiveSpecError(msg)
    return array


def require_binary_labels(target: np.ndarray, *, family_id: str) -> None:
    """Reject non-binary classification targets (D-S042-08)."""
    classes = np.unique(target)
    if classes.size != 2:
        msg = f"{family_id} supports binary classification only; got {int(classes.size)} classes"
        raise PredictiveSpecError(msg)


def reject_non_train_metadata(sample_metadata: object, *, n_rows: int) -> None:
    """Reject PURGED / EMBARGOED / TEST rows at fit time."""
    roles = _fold_roles_from_metadata(sample_metadata)
    if roles is None:
        return
    if len(roles) != n_rows:
        msg = f"sample_metadata fold roles length {len(roles)} does not match feature rows {n_rows}"
        raise PredictiveSpecError(msg)
    require_train_only_fit_roles(roles)


def _fold_roles_from_metadata(sample_metadata: object) -> tuple[FoldRole, ...] | None:
    if sample_metadata is None:
        return None
    raw: object = sample_metadata
    if isinstance(sample_metadata, Mapping):
        if "fold_role" in sample_metadata:
            raw = sample_metadata["fold_role"]
        elif "fold_roles" in sample_metadata:
            raw = sample_metadata["fold_roles"]
        else:
            return None
    if isinstance(raw, np.ndarray):
        raw = raw.tolist()
    if isinstance(raw, (str, bytes)):
        return None
    if not isinstance(raw, Sequence):
        return None
    roles: list[FoldRole] = []
    for item in raw:
        if isinstance(item, FoldRole):
            roles.append(item)
            continue
        if isinstance(item, str):
            try:
                roles.append(FoldRole(item))
            except ValueError:
                return None
            continue
        return None
    return tuple(roles)


def reject_unknown_hyperparameters(
    hyperparameters: Mapping[str, Any],
    *,
    allowed: frozenset[str],
    family_id: str,
) -> None:
    """Reject hyperparameter keys outside the family allow-list (D-S042-10)."""
    unknown = sorted(key for key in hyperparameters if key not in allowed)
    if unknown:
        msg = f"unknown hyperparameters for {family_id}: {unknown}"
        raise PredictiveSpecError(msg)


def unique_hyperparameter_alias(
    hyperparameters: Mapping[str, Any],
    aliases: tuple[str, ...],
    *,
    family_id: str,
) -> object | None:
    """Return the single present alias, or ``None`` when none are set."""
    present = [key for key in aliases if key in hyperparameters]
    if len(present) > 1:
        msg = f"{family_id} accepts only one of {list(aliases)}; got {present}"
        raise PredictiveSpecError(msg)
    if not present:
        return None
    value: object = hyperparameters[present[0]]
    return value


def as_lower_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower()


def json_stable_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    """JSON-stable copy of library ``get_params()`` for ``describe()``."""
    converted = {str(key): _json_stable_value(value) for key, value in values.items()}
    try:
        canonical = json.dumps(converted, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        msg = "resolved estimator params must be JSON-serializable"
        raise PredictiveSpecError(msg) from exc
    loaded = json.loads(canonical)
    if not isinstance(loaded, dict):
        msg = "resolved estimator params must be a mapping"
        raise PredictiveSpecError(msg)
    return loaded


def _json_stable_value(value: object) -> object:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not np.isfinite(value):
            return None
        return value
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        converted = float(value)
        if not np.isfinite(converted):
            return None
        return converted
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.ndarray):
        return [_json_stable_value(item) for item in value.tolist()]
    if isinstance(value, Mapping):
        return {str(key): _json_stable_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_stable_value(item) for item in value]
    return str(value)
