"""Seeded CPU training loop for neural PredictiveEstimator adapters (D-S043-13/14).

Import torch inside functions only. Do not import torch at module level.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from trading_framework.infrastructure.ml.torch._guards import ResolvedTorchHyperparameters
from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.estimators import TaskType


@dataclass(frozen=True, slots=True)
class InnerTrainingResult:
    """Learning-curve facts from the inner-train / inner-val run."""

    stopping_epoch: int
    train_loss: tuple[float, ...]
    validation_loss: tuple[float, ...]


def configure_torch_determinism(torch: Any, *, seed: int) -> Any:
    """Seed RNGs, pin one thread, and require deterministic algorithms."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    generator = torch.Generator()
    generator.manual_seed(seed)
    return generator


def build_feedforward_module(
    torch: Any,
    *,
    n_features: int,
    hidden_sizes: Sequence[int],
    dropout: float,
) -> Any:
    """Declared MLP: Linear-ReLU-(Dropout) blocks then a scalar output."""
    nn = torch.nn
    layers: list[Any] = []
    in_features = n_features
    for hidden in hidden_sizes:
        layers.append(nn.Linear(in_features, int(hidden)))
        layers.append(nn.ReLU())
        if dropout > 0.0:
            layers.append(nn.Dropout(float(dropout)))
        in_features = int(hidden)
    layers.append(nn.Linear(in_features, 1))
    return nn.Sequential(*layers)


def build_recurrent_module(
    torch: Any,
    *,
    cell: str,
    n_features: int,
    hidden_size: int,
    num_layers: int,
    dropout: float,
) -> Any:
    """Declared LSTM/GRU: last timestep then a scalar head (D-S043-12)."""
    nn = torch.nn
    if cell == "lstm":
        recurrent_cls = nn.LSTM
    elif cell == "gru":
        recurrent_cls = nn.GRU
    else:
        msg = f"unsupported sequence cell {cell!r}"
        raise PredictiveSpecError(msg)
    recurrent_dropout = float(dropout) if num_layers > 1 else 0.0

    class _RecurrentEstimator(nn.Module):  # type: ignore[name-defined,misc]
        def __init__(self) -> None:
            super().__init__()
            self.rnn = recurrent_cls(
                input_size=int(n_features),
                hidden_size=int(hidden_size),
                num_layers=int(num_layers),
                batch_first=True,
                dropout=recurrent_dropout,
                bidirectional=False,
            )
            self.head = nn.Linear(int(hidden_size), 1)

        def forward(self, features: Any) -> Any:
            encoded, _state = self.rnn(features)
            return self.head(encoded[:, -1, :])

    return _RecurrentEstimator()


def train_with_early_stopping(
    torch: Any,
    *,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    resolved: ResolvedTorchHyperparameters,
    task_type: TaskType,
    seed: int,
    build_model: Callable[[Any], Any],
) -> tuple[Any, InnerTrainingResult]:
    """Train on inner-train, early-stop on inner-val loss, never on TEST."""
    generator = configure_torch_determinism(torch, seed=seed)
    model = build_model(torch)
    criterion = _criterion(torch, task_type=task_type)
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=resolved.learning_rate,
        weight_decay=resolved.weight_decay,
    )
    train_loader = _loader(
        torch,
        x_train,
        y_train,
        batch_size=resolved.batch_size,
        generator=generator,
        shuffle=True,
    )
    val_loader = _loader(
        torch,
        x_val,
        y_val,
        batch_size=resolved.batch_size,
        generator=None,
        shuffle=False,
    )
    best_state: dict[str, Any] | None = None
    best_val = float("inf")
    best_epoch = 0
    wait = 0
    train_losses: list[float] = []
    val_losses: list[float] = []
    for epoch in range(1, resolved.max_epochs + 1):
        train_loss = _run_epoch(
            torch,
            model,
            train_loader,
            criterion,
            optimizer=optimizer,
        )
        val_loss = _run_epoch(torch, model, val_loader, criterion, optimizer=None)
        train_losses.append(train_loss)
        val_losses.append(val_loss)
        if val_loss < best_val - resolved.min_delta:
            best_val = val_loss
            best_epoch = epoch
            best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
            wait = 0
            continue
        wait += 1
        if wait >= resolved.patience:
            break
    if best_state is not None:
        model.load_state_dict(best_state)
    stopping_epoch = best_epoch if best_epoch > 0 else 1
    return model, InnerTrainingResult(
        stopping_epoch=stopping_epoch,
        train_loss=tuple(train_losses),
        validation_loss=tuple(val_losses),
    )


def refit_for_epochs(
    torch: Any,
    *,
    features: np.ndarray,
    target: np.ndarray,
    resolved: ResolvedTorchHyperparameters,
    task_type: TaskType,
    seed: int,
    epochs: int,
    build_model: Callable[[Any], Any],
) -> Any:
    """Refit on full outer TRAIN for exactly ``epochs`` steps, no early stop."""
    generator = configure_torch_determinism(torch, seed=seed)
    model = build_model(torch)
    criterion = _criterion(torch, task_type=task_type)
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=resolved.learning_rate,
        weight_decay=resolved.weight_decay,
    )
    loader = _loader(
        torch,
        features,
        target,
        batch_size=resolved.batch_size,
        generator=generator,
        shuffle=True,
    )
    for _ in range(epochs):
        _run_epoch(torch, model, loader, criterion, optimizer=optimizer)
    model.eval()
    return model


def forward_logits(torch: Any, model: Any, features: np.ndarray) -> np.ndarray:
    """Run a fitted module on CPU float32 features and return float64 logits."""
    model.eval()
    tensor = torch.as_tensor(np.asarray(features, dtype=np.float32), dtype=torch.float32)
    with torch.no_grad():
        logits = model(tensor).squeeze(-1)
    return np.asarray(logits.detach().cpu().numpy(), dtype=np.float64)


def _criterion(torch: Any, *, task_type: TaskType) -> Any:
    if task_type is TaskType.CLASSIFICATION:
        return torch.nn.BCEWithLogitsLoss()
    return torch.nn.MSELoss()


def _loader(
    torch: Any,
    features: np.ndarray,
    target: np.ndarray,
    *,
    batch_size: int,
    generator: Any,
    shuffle: bool,
) -> Any:
    tensor_x = torch.as_tensor(np.asarray(features, dtype=np.float32), dtype=torch.float32)
    tensor_y = torch.as_tensor(np.asarray(target, dtype=np.float32), dtype=torch.float32)
    dataset = torch.utils.data.TensorDataset(tensor_x, tensor_y)
    return torch.utils.data.DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        generator=generator if shuffle else None,
        drop_last=False,
        num_workers=0,
    )


def _run_epoch(
    torch: Any,
    model: Any,
    loader: Any,
    criterion: Any,
    *,
    optimizer: Any | None,
) -> float:
    training = optimizer is not None
    model.train(training)
    total = 0.0
    count = 0
    context = torch.enable_grad() if training else torch.no_grad()
    with context:
        for batch_x, batch_y in loader:
            logits = model(batch_x).squeeze(-1)
            loss = criterion(logits, batch_y)
            if optimizer is not None:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            batch_count = int(batch_y.shape[0])
            total += float(loss.item()) * batch_count
            count += batch_count
    if count == 0:
        return 0.0
    return total / count
