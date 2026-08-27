"""Library-free validation for torch family specs (D-S043-08 / D-S043-12 / D-S043-13)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.selection import require_early_stopping_eval_roles
from trading_framework.research.predictive.splitting import FoldRole
from trading_framework.research.predictive.windows import SequenceWindowSpec

_MAX_EPOCHS_CAP = 200
_DEFAULT_MAX_EPOCHS = 50
_DEFAULT_BATCH_SIZE = 32
_DEFAULT_LEARNING_RATE = 1e-3
_DEFAULT_WEIGHT_DECAY = 0.0
_DEFAULT_PATIENCE = 5
_DEFAULT_MIN_DELTA = 0.0
_DEFAULT_DROPOUT = 0.0
_DEFAULT_HIDDEN_SIZES = (32, 16)
_DEFAULT_HIDDEN_SIZE = 32
_MAX_HIDDEN_SIZE = 128
_ALLOWED_NUM_LAYERS = frozenset({1, 2})
_ALLOWED_ACTIVATION = "relu"
_ALLOWED_CELLS = frozenset({"lstm", "gru"})
_ALLOWED_OPTIMIZER = "adam"
_ALLOWED_DEVICE = "cpu"
_REGRESSION_LOSS = "mse"
_CLASSIFICATION_LOSS = "bce_with_logits"
_REPRO_ATOL = 1e-5
_REPRO_RTOL = 1e-4
_GPU_DEVICE_TOKENS = frozenset({"cuda", "gpu", "mps"})
_WINDOW_METADATA_KEYS = frozenset(
    {"window_spec", "sequence_window_spec", "sequence_windows", "windows"}
)
_EARLY_STOP_METADATA_KEYS = frozenset(
    {"early_stopping_eval_role", "eval_fold_role", "early_stopping_on"}
)
_SHARED_USER_KEYS = frozenset(
    {
        "max_epochs",
        "batch_size",
        "learning_rate",
        "weight_decay",
        "patience",
        "min_delta",
        "dropout",
        "device",
        "optimizer",
        "loss",
        "num_threads",
        "early_stopping_eval_role",
    }
)
_FEEDFORWARD_USER_KEYS = _SHARED_USER_KEYS | frozenset({"hidden_sizes", "activation"})
_SEQUENCE_USER_KEYS = _SHARED_USER_KEYS | frozenset({"hidden_size", "num_layers", "bidirectional"})


@dataclass(frozen=True, slots=True)
class ResolvedTorchHyperparameters:
    """Declared neural hyperparameters after validation and defaults."""

    max_epochs: int
    batch_size: int
    learning_rate: float
    weight_decay: float
    patience: int
    min_delta: float
    dropout: float
    hidden_sizes: tuple[int, ...] | None
    hidden_size: int | None
    num_layers: int | None
    cell: str | None
    activation: str | None
    device: str
    optimizer: str
    loss: str
    num_threads: int
    reproducibility_atol: float
    reproducibility_rtol: float

    def as_json_mapping(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "batch_size": self.batch_size,
            "device": self.device,
            "dropout": self.dropout,
            "learning_rate": self.learning_rate,
            "loss": self.loss,
            "max_epochs": self.max_epochs,
            "min_delta": self.min_delta,
            "num_threads": self.num_threads,
            "optimizer": self.optimizer,
            "patience": self.patience,
            "reproducibility_atol": self.reproducibility_atol,
            "reproducibility_rtol": self.reproducibility_rtol,
            "weight_decay": self.weight_decay,
        }
        if self.cell is None:
            payload["activation"] = self.activation
            payload["hidden_sizes"] = list(self.hidden_sizes or ())
        else:
            payload["cell"] = self.cell
            payload["hidden_size"] = self.hidden_size
            payload["num_layers"] = self.num_layers
        return payload


def reject_unknown_hyperparameters(
    hyperparameters: Mapping[str, Any],
    *,
    family_id: str,
    allowed: frozenset[str] = _FEEDFORWARD_USER_KEYS,
) -> None:
    unknown = sorted(key for key in hyperparameters if key not in allowed)
    if unknown:
        msg = f"unknown hyperparameters for {family_id}: {unknown}"
        raise PredictiveSpecError(msg)


def reject_gpu_device(hyperparameters: Mapping[str, Any], *, family_id: str) -> None:
    raw_device = hyperparameters.get("device")
    if raw_device is None:
        return
    device = str(raw_device).strip().lower()
    token = device.split(":", maxsplit=1)[0]
    if device != _ALLOWED_DEVICE or token in _GPU_DEVICE_TOKENS:
        msg = f"{family_id} rejects GPU/CUDA/MPS device {raw_device!r}; CPU-only (D-S043-14)"
        raise PredictiveSpecError(msg)


def _resolve_shared_hyperparameters(
    hyperparameters: Mapping[str, Any],
    *,
    family_id: str,
    is_classification: bool,
    allowed: frozenset[str],
) -> dict[str, Any]:
    reject_unknown_hyperparameters(hyperparameters, family_id=family_id, allowed=allowed)
    reject_gpu_device(hyperparameters, family_id=family_id)
    _reject_outer_test_early_stopping_config(hyperparameters)
    optimizer = _optional_str(hyperparameters.get("optimizer"), default=_ALLOWED_OPTIMIZER)
    if optimizer != _ALLOWED_OPTIMIZER:
        msg = f"{family_id} supports optimizer {_ALLOWED_OPTIMIZER!r} only; got {optimizer!r}"
        raise PredictiveSpecError(msg)
    expected_loss = _CLASSIFICATION_LOSS if is_classification else _REGRESSION_LOSS
    loss = _optional_str(hyperparameters.get("loss"), default=expected_loss)
    if loss != expected_loss:
        msg = f"{family_id} requires loss {expected_loss!r}; got {loss!r}"
        raise PredictiveSpecError(msg)
    num_threads = _optional_positive_int(hyperparameters.get("num_threads"), default=1)
    if num_threads != 1:
        msg = f"{family_id} pins num_threads=1; got {num_threads}"
        raise PredictiveSpecError(msg)
    return {
        "max_epochs": _bounded_max_epochs(hyperparameters.get("max_epochs"), family_id=family_id),
        "batch_size": _optional_positive_int(
            hyperparameters.get("batch_size"), default=_DEFAULT_BATCH_SIZE
        ),
        "learning_rate": _learning_rate(hyperparameters.get("learning_rate")),
        "weight_decay": _non_negative_float(
            hyperparameters.get("weight_decay"), default=_DEFAULT_WEIGHT_DECAY
        ),
        "patience": _optional_positive_int(
            hyperparameters.get("patience"), default=_DEFAULT_PATIENCE
        ),
        "min_delta": _non_negative_float(
            hyperparameters.get("min_delta"), default=_DEFAULT_MIN_DELTA
        ),
        "dropout": _dropout(hyperparameters.get("dropout")),
        "device": _ALLOWED_DEVICE,
        "optimizer": optimizer,
        "loss": loss,
        "num_threads": 1,
        "reproducibility_atol": _REPRO_ATOL,
        "reproducibility_rtol": _REPRO_RTOL,
    }


def resolve_feedforward_hyperparameters(
    hyperparameters: Mapping[str, Any],
    *,
    family_id: str,
    is_classification: bool,
) -> ResolvedTorchHyperparameters:
    shared = _resolve_shared_hyperparameters(
        hyperparameters,
        family_id=family_id,
        is_classification=is_classification,
        allowed=_FEEDFORWARD_USER_KEYS,
    )
    activation = _optional_str(hyperparameters.get("activation"), default=_ALLOWED_ACTIVATION)
    if activation != _ALLOWED_ACTIVATION:
        msg = f"{family_id} supports activation {_ALLOWED_ACTIVATION!r} only; got {activation!r}"
        raise PredictiveSpecError(msg)
    return ResolvedTorchHyperparameters(
        **shared,
        hidden_sizes=_hidden_sizes(hyperparameters.get("hidden_sizes")),
        hidden_size=None,
        num_layers=None,
        cell=None,
        activation=activation,
    )


def resolve_sequence_hyperparameters(
    hyperparameters: Mapping[str, Any],
    *,
    family_id: str,
    cell: str,
    is_classification: bool,
) -> ResolvedTorchHyperparameters:
    if cell not in _ALLOWED_CELLS:
        msg = f"unsupported sequence cell {cell!r}"
        raise PredictiveSpecError(msg)
    shared = _resolve_shared_hyperparameters(
        hyperparameters,
        family_id=family_id,
        is_classification=is_classification,
        allowed=_SEQUENCE_USER_KEYS,
    )
    bidirectional = hyperparameters.get("bidirectional")
    if bidirectional not in (None, False, 0):
        msg = f"{family_id} rejects bidirectional recurrent layers"
        raise PredictiveSpecError(msg)
    hidden_size = _optional_positive_int(
        hyperparameters.get("hidden_size"), default=_DEFAULT_HIDDEN_SIZE
    )
    if hidden_size > _MAX_HIDDEN_SIZE:
        msg = f"{family_id} hidden_size must be <= {_MAX_HIDDEN_SIZE}, got {hidden_size}"
        raise PredictiveSpecError(msg)
    num_layers = _optional_positive_int(hyperparameters.get("num_layers"), default=1)
    if num_layers not in _ALLOWED_NUM_LAYERS:
        msg = f"{family_id} num_layers must be 1 or 2, got {num_layers}"
        raise PredictiveSpecError(msg)
    return ResolvedTorchHyperparameters(
        **shared,
        hidden_sizes=None,
        hidden_size=hidden_size,
        num_layers=num_layers,
        cell=cell,
        activation=None,
    )


def reject_sequence_window_spec(sample_metadata: object, *, family_id: str) -> None:
    """Tabular families reject a ``SequenceWindowSpec`` if it is ever passed."""
    if isinstance(sample_metadata, SequenceWindowSpec):
        msg = f"{family_id} is tabular and rejects SequenceWindowSpec"
        raise PredictiveSpecError(msg)
    if not isinstance(sample_metadata, Mapping):
        return
    for key in _WINDOW_METADATA_KEYS:
        value = sample_metadata.get(key)
        if value is None:
            continue
        msg = f"{family_id} is tabular and rejects SequenceWindowSpec"
        raise PredictiveSpecError(msg)


def require_sequence_window_spec(sample_metadata: object, *, family_id: str) -> SequenceWindowSpec:
    """Sequence families require a ``SequenceWindowSpec`` (D-S043-08)."""
    if isinstance(sample_metadata, SequenceWindowSpec):
        return sample_metadata
    if isinstance(sample_metadata, Mapping):
        for key in ("window_spec", "sequence_window_spec"):
            value = sample_metadata.get(key)
            if value is None:
                continue
            if isinstance(value, SequenceWindowSpec):
                return value
            if isinstance(value, Mapping):
                return SequenceWindowSpec.from_dict(value)
    msg = f"{family_id} requires SequenceWindowSpec"
    raise PredictiveSpecError(msg)


def reject_outer_test_early_stopping(
    sample_metadata: object,
    hyperparameters: Mapping[str, Any],
) -> None:
    """Using outer TEST (or leak-guard rows) as an early-stopping set is invalid."""
    _reject_outer_test_early_stopping_config(hyperparameters)
    if sample_metadata is None:
        return
    if isinstance(sample_metadata, Mapping):
        for key in _EARLY_STOP_METADATA_KEYS:
            raw = sample_metadata.get(key)
            if raw is None:
                continue
            _reject_eval_role_value(raw)
        roles = sample_metadata.get("early_stopping_roles")
        if roles is not None:
            require_early_stopping_eval_roles(_coerce_roles(roles))
        return
    if isinstance(sample_metadata, Sequence) and not isinstance(sample_metadata, (str, bytes)):
        return


def _reject_outer_test_early_stopping_config(hyperparameters: Mapping[str, Any]) -> None:
    raw = hyperparameters.get("early_stopping_eval_role")
    if raw is None:
        return
    _reject_eval_role_value(raw)


def _reject_eval_role_value(raw: object) -> None:
    if isinstance(raw, FoldRole):
        role = raw
    else:
        try:
            role = FoldRole(str(raw))
        except ValueError as exc:
            msg = f"invalid early-stopping eval role: {raw!r}"
            raise PredictiveSpecError(msg) from exc
    require_early_stopping_eval_roles((role,))


def _coerce_roles(raw: object) -> tuple[FoldRole, ...]:
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        msg = "early_stopping_roles must be a sequence of fold roles"
        raise PredictiveSpecError(msg)
    roles: list[FoldRole] = []
    for item in raw:
        if isinstance(item, FoldRole):
            roles.append(item)
            continue
        try:
            roles.append(FoldRole(str(item)))
        except ValueError as exc:
            msg = f"invalid early-stopping eval role: {item!r}"
            raise PredictiveSpecError(msg) from exc
    return tuple(roles)


def _bounded_max_epochs(raw: object, *, family_id: str) -> int:
    value = _optional_positive_int(raw, default=_DEFAULT_MAX_EPOCHS)
    if value > _MAX_EPOCHS_CAP:
        msg = f"{family_id} max_epochs must be <= {_MAX_EPOCHS_CAP}, got {value}"
        raise PredictiveSpecError(msg)
    return value


def _hidden_sizes(raw: object) -> tuple[int, ...]:
    if raw is None:
        return _DEFAULT_HIDDEN_SIZES
    if isinstance(raw, bool) or not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        msg = "hidden_sizes must be a sequence of positive integers, length 1..3"
        raise PredictiveSpecError(msg)
    if not (1 <= len(raw) <= 3):
        msg = f"hidden_sizes length must be 1..3, got {len(raw)}"
        raise PredictiveSpecError(msg)
    sizes: list[int] = []
    for item in raw:
        if isinstance(item, bool) or not isinstance(item, int) or item < 1:
            msg = "hidden_sizes entries must be positive integers"
            raise PredictiveSpecError(msg)
        sizes.append(item)
    return tuple(sizes)


def _learning_rate(raw: object) -> float:
    value = _optional_float(raw, default=_DEFAULT_LEARNING_RATE)
    if not (0.0 < value <= 1.0):
        msg = f"learning_rate must be in (0, 1], got {value}"
        raise PredictiveSpecError(msg)
    return value


def _dropout(raw: object) -> float:
    value = _optional_float(raw, default=_DEFAULT_DROPOUT)
    if not (0.0 <= value <= 0.5):
        msg = f"dropout must be in [0, 0.5], got {value}"
        raise PredictiveSpecError(msg)
    return value


def _non_negative_float(raw: object, *, default: float) -> float:
    value = _optional_float(raw, default=default)
    if value < 0.0:
        msg = f"expected a non-negative number, got {value}"
        raise PredictiveSpecError(msg)
    return value


def _optional_positive_int(raw: object, *, default: int) -> int:
    if raw is None:
        return default
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        msg = f"expected a positive integer, got {raw!r}"
        raise PredictiveSpecError(msg)
    return raw


def _optional_float(raw: object, *, default: float) -> float:
    if raw is None:
        return default
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        msg = f"expected a number, got {raw!r}"
        raise PredictiveSpecError(msg)
    return float(raw)


def _optional_str(raw: object, *, default: str) -> str:
    if raw is None:
        return default
    return str(raw).strip().lower()
