"""Run Predictive Research: per-fold fit on TRAIN, predict on TEST, persist."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from trading_framework import __version__ as framework_version
from trading_framework.application.predictive_research.analyze_predictive_run import (
    AnalyzePredictiveRunRequest,
    analyze_predictive_run,
    metrics_report_from_envelopes,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.ml.registry import dump_fitted_estimator, resolve_estimator
from trading_framework.infrastructure.storage.paths import (
    predictive_research_run_model_path,
    predictive_research_run_selection_path,
)
from trading_framework.research.datasets.predictive import (
    PredictiveDatasetEnvelope,
    PredictiveDatasetRef,
    PredictiveDatasetRepository,
)
from trading_framework.research.datasets.predictive_run import (
    PREDICTIVE_RUN_SCHEMA_VERSION,
    PredictiveRunEnvelope,
    PredictiveRunManifest,
    PredictiveRunRef,
    PredictiveRunRepository,
    compute_run_fingerprint,
    derive_predictive_run_id,
)
from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.estimators import (
    EstimatorSpec,
    FittedPredictiveEstimator,
    TaskType,
)
from trading_framework.research.predictive.labels import LabelKind
from trading_framework.research.predictive.metrics import (
    PredictiveMetricsReport,
    selection_metric_value,
)
from trading_framework.research.predictive.preprocessing import (
    PreprocessingSpec,
    default_preprocessing_spec,
    require_train_only_fit_roles,
)
from trading_framework.research.predictive.selection import (
    CandidateFoldScore,
    CandidateSetSpec,
    FoldSelectionTrace,
    SelectionTrace,
    candidate_identity_hash,
    require_early_stopping_eval_roles,
    select_winning_index,
    split_inner_train_validation,
)
from trading_framework.research.predictive.splitting import FoldRole
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock

_MATRIX_METADATA_COLUMNS = frozenset(
    {
        "entity_id",
        "horizon_bars",
        "detected_at",
        "available_at",
        "label_end_at",
        "label",
        "forward_return",
        "outcome_status",
        "fold_id",
        "fold_role",
    }
)


class PredictiveRunError(ValidationError):
    """Raised when Predictive Research run orchestration fails."""


@dataclass(frozen=True, slots=True)
class RunPredictiveResearchRequest:
    """Input for one Predictive Research run."""

    dataset_ref: PredictiveDatasetRef
    estimator: EstimatorSpec
    storage_root: Path
    preprocessing: PreprocessingSpec | None = None
    persist: bool = True
    clock: Clock | None = None
    dataset_repository: PredictiveDatasetRepository | None = None
    run_repository: PredictiveRunRepository | None = None
    candidate_set: CandidateSetSpec | None = None


@dataclass(frozen=True, slots=True)
class RunPredictiveResearchResult:
    """Outcome of one Predictive Research run."""

    run_id: str
    run_ref: PredictiveRunRef
    fingerprint: str
    envelope: PredictiveRunEnvelope
    persisted: bool
    metrics: PredictiveMetricsReport
    selection_trace: SelectionTrace | None = None


def run_predictive_research(request: RunPredictiveResearchRequest) -> RunPredictiveResearchResult:
    """Load a dataset envelope, fit per fold on TRAIN, predict on TEST, persist.

    PURGED and EMBARGOED rows never reach ``fit()``. Application resolves
    estimators through ``infrastructure.ml.registry`` only. A run with
    ``candidate_set`` selects inside outer TRAIN and touches TEST once.
    """
    preprocessing = request.preprocessing or default_preprocessing_spec()
    dataset_repository = request.dataset_repository or PredictiveDatasetRepository(
        request.storage_root
    )
    envelope = dataset_repository.read(request.dataset_ref)
    candidate_set = request.candidate_set
    declared_spec = candidate_set.candidates[0] if candidate_set is not None else request.estimator
    _validate_dataset_for_estimator(envelope, declared_spec)

    feature_columns = _feature_columns(envelope.features)
    prediction_frames: list[pl.DataFrame] = []
    model_blobs: dict[int, bytes] = {}
    description_payload: dict[str, Any] | None = None
    library = ""
    library_version = ""
    fold_traces: list[FoldSelectionTrace] = []
    winner_spec = request.estimator

    fold_ids = [boundary.fold_id for boundary in envelope.folds]
    if not fold_ids:
        msg = "dataset envelope has no folds"
        raise PredictiveRunError(msg)

    single_estimator = None
    if candidate_set is None:
        single_estimator = resolve_estimator(request.estimator, preprocessing=preprocessing)

    for fold_id in fold_ids:
        train_rows, test_rows = _train_and_test_rows(envelope.features, fold_id)
        if candidate_set is not None:
            train_rows = train_rows.sort("available_at")
        train_roles = _fold_roles(train_rows)
        require_train_only_fit_roles(train_roles)
        if candidate_set is not None:
            fitted, winner_spec, fold_trace = _select_and_refit_fold(
                candidate_set,
                train_rows=train_rows,
                feature_columns=feature_columns,
                fold_id=fold_id,
                preprocessing=preprocessing,
            )
            fold_traces.append(fold_trace)
        else:
            assert single_estimator is not None
            train_features = _feature_matrix(train_rows, feature_columns)
            train_target = _label_vector(train_rows)
            fitted = single_estimator.fit(train_features, train_target, train_roles)
        description = fitted.describe()
        if description_payload is None:
            description_payload = {
                "library": description.library,
                "version": description.version,
                "resolved_params": dict(description.resolved_params),
            }
            library = description.library
            library_version = description.version
        prediction_frames.append(_prediction_frame(fitted, test_rows, feature_columns, fold_id))
        model_blobs[fold_id] = dump_fitted_estimator(fitted)

    if description_payload is None:
        msg = "run produced no fitted folds"
        raise PredictiveRunError(msg)

    selection_trace = None
    candidate_payload = None
    selection_trace_file = None
    if candidate_set is not None:
        selection_trace = SelectionTrace(
            selection_metric=candidate_set.selection_metric,
            inner_validation_fraction=candidate_set.inner_validation_fraction,
            folds=tuple(fold_traces),
        )
        candidate_payload = candidate_set.to_dict()
        selection_trace_file = "selection.json"

    fingerprint = compute_run_fingerprint(
        dataset_fingerprint=envelope.manifest.dataset_fingerprint,
        estimator_spec=winner_spec,
        preprocessing_spec=preprocessing,
        library=library,
        library_version=library_version,
        framework_version=framework_version,
        candidate_set=candidate_payload,
    )
    run_id = derive_predictive_run_id(fingerprint)
    clock = request.clock or SystemClock()
    model_files = {
        str(fold_id): _relative_model_path(request.storage_root, run_id, fold_id)
        for fold_id in model_blobs
    }
    run_envelope = PredictiveRunEnvelope(
        manifest=PredictiveRunManifest(
            schema_version=PREDICTIVE_RUN_SCHEMA_VERSION,
            run_id=run_id,
            run_fingerprint=fingerprint,
            dataset_id=envelope.manifest.dataset_id,
            dataset_fingerprint=envelope.manifest.dataset_fingerprint,
            estimator_spec=winner_spec.to_dict(),
            preprocessing_spec=preprocessing.to_dict(),
            library=library,
            library_version=library_version,
            framework_version=framework_version,
            created_at_utc=clock.now(),
            model_files=model_files,
            estimator_description=description_payload,
            candidate_set=candidate_payload,
            selection_trace_file=selection_trace_file,
        ),
        predictions=pl.concat(prediction_frames, how="vertical"),
    )
    run_ref = PredictiveRunRef(run_id=run_id)
    persisted = False
    if request.persist:
        run_repository = request.run_repository or PredictiveRunRepository(request.storage_root)
        run_ref = run_repository.write(run_envelope, model_blobs=model_blobs)
        persisted = True
        if selection_trace is not None:
            selection_path = predictive_research_run_selection_path(request.storage_root, run_id)
            selection_path.write_text(
                json.dumps(selection_trace.to_dict(), indent=2),
                encoding="utf-8",
            )
        metrics = analyze_predictive_run(
            AnalyzePredictiveRunRequest(
                run_ref=run_ref,
                storage_root=request.storage_root,
                persist=True,
                run_repository=run_repository,
                dataset_repository=dataset_repository,
            )
        ).report
    else:
        metrics = metrics_report_from_envelopes(run_envelope, envelope.features)
    return RunPredictiveResearchResult(
        run_id=run_id,
        run_ref=run_ref,
        fingerprint=fingerprint,
        envelope=run_envelope,
        persisted=persisted,
        metrics=metrics,
        selection_trace=selection_trace,
    )


def _select_and_refit_fold(
    candidate_set: CandidateSetSpec,
    *,
    train_rows: pl.DataFrame,
    feature_columns: tuple[str, ...],
    fold_id: int,
    preprocessing: PreprocessingSpec,
) -> tuple[FittedPredictiveEstimator, EstimatorSpec, FoldSelectionTrace]:
    inner_train_idx, inner_val_idx = split_inner_train_validation(
        train_rows.height,
        inner_validation_fraction=candidate_set.inner_validation_fraction,
    )
    inner_train = train_rows[inner_train_idx.start : inner_train_idx.stop]
    inner_val = train_rows[inner_val_idx.start : inner_val_idx.stop]
    inner_train_roles = _fold_roles(inner_train)
    inner_val_roles = _fold_roles(inner_val)
    require_train_only_fit_roles(inner_train_roles)
    if candidate_set.early_stopping_rounds is not None:
        require_early_stopping_eval_roles(inner_val_roles)
    inner_train_features = _feature_matrix(inner_train, feature_columns)
    inner_train_target = _label_vector(inner_train)
    inner_val_features = _feature_matrix(inner_val, feature_columns)
    inner_val_target = _label_vector(inner_val)
    scores: list[float | None] = []
    for candidate in candidate_set.candidates:
        estimator = resolve_estimator(candidate, preprocessing=preprocessing)
        fitted = estimator.fit(inner_train_features, inner_train_target, inner_train_roles)
        predicted = np.asarray(fitted.predict(inner_val_features), dtype=np.float64).reshape(-1)
        score_vector = _score_vector(fitted, inner_val_features, n_rows=inner_val.height)
        scores.append(
            selection_metric_value(
                candidate_set.selection_metric.value,
                y_true=inner_val_target,
                y_pred=predicted,
                y_score=score_vector,
            )
        )
    winner_index = select_winning_index(scores)
    winner = candidate_set.candidates[winner_index]
    refit_estimator = resolve_estimator(winner, preprocessing=preprocessing)
    full_roles = _fold_roles(train_rows)
    refitted = refit_estimator.fit(
        _feature_matrix(train_rows, feature_columns),
        _label_vector(train_rows),
        full_roles,
    )
    fold_scores = tuple(
        CandidateFoldScore(
            family=candidate.family,
            hyperparameters=candidate.hyperparameters,
            seed=candidate.seed,
            identity_hash=candidate_identity_hash(candidate),
            inner_validation_score=score,
            selected=index == winner_index,
        )
        for index, (candidate, score) in enumerate(
            zip(candidate_set.candidates, scores, strict=True)
        )
    )
    return (
        refitted,
        winner,
        FoldSelectionTrace(fold_id=fold_id, winner=winner, candidates=fold_scores),
    )


def _prediction_frame(
    fitted: FittedPredictiveEstimator,
    test_rows: pl.DataFrame,
    feature_columns: tuple[str, ...],
    fold_id: int,
) -> pl.DataFrame:
    test_features = _feature_matrix(test_rows, feature_columns)
    y_pred = np.asarray(fitted.predict(test_features), dtype=np.float64).reshape(-1)
    if y_pred.shape[0] != test_rows.height:
        msg = (
            f"fold {fold_id} predict length {y_pred.shape[0]} "
            f"does not match TEST rows {test_rows.height}"
        )
        raise PredictiveRunError(msg)
    y_proba = _positive_class_proba(
        fitted.predict_proba(test_features),
        n_rows=test_rows.height,
    )
    return pl.DataFrame(
        {
            "entity_id": test_rows.get_column("entity_id").to_list(),
            "fold_id": [fold_id] * test_rows.height,
            "y_true": test_rows.get_column("label").to_list(),
            "y_pred": y_pred.tolist(),
            "y_proba": y_proba,
            "forward_return": test_rows.get_column("forward_return").to_list(),
        },
        schema={
            "entity_id": pl.String(),
            "fold_id": pl.Int64(),
            "y_true": pl.Float64(),
            "y_pred": pl.Float64(),
            "y_proba": pl.Float64(),
            "forward_return": pl.Float64(),
        },
    )


def _score_vector(
    fitted: FittedPredictiveEstimator,
    features: np.ndarray,
    *,
    n_rows: int,
) -> np.ndarray:
    proba = _positive_class_proba(fitted.predict_proba(features), n_rows=n_rows)
    if any(value is None for value in proba):
        return np.asarray(fitted.predict(features), dtype=np.float64).reshape(-1)
    return np.asarray(proba, dtype=np.float64)


def _validate_dataset_for_estimator(
    envelope: PredictiveDatasetEnvelope,
    spec: EstimatorSpec,
) -> None:
    if "forward_return" not in envelope.features.columns:
        msg = "labelled matrix must retain forward_return beside label"
        raise PredictiveRunError(msg)
    kind = _label_kind(envelope)
    if kind is LabelKind.TERNARY:
        msg = "S040 does not train TERNARY datasets; multinomial estimators are a later increment"
        raise PredictiveSpecError(msg)
    if spec.task_type is TaskType.CLASSIFICATION and kind is not LabelKind.BINARY:
        msg = (
            f"estimator family {spec.family!r} requires a BINARY labelled dataset, got {kind.value}"
        )
        raise PredictiveSpecError(msg)
    if spec.task_type is TaskType.REGRESSION and kind is not LabelKind.REGRESSION:
        msg = (
            f"estimator family {spec.family!r} requires a REGRESSION labelled dataset, "
            f"got {kind.value}"
        )
        raise PredictiveSpecError(msg)


def _label_kind(envelope: PredictiveDatasetEnvelope) -> LabelKind:
    label_payload = envelope.manifest.study_spec.get("label")
    if not isinstance(label_payload, dict) or "kind" not in label_payload:
        msg = "dataset manifest study_spec is missing label.kind"
        raise PredictiveRunError(msg)
    try:
        return LabelKind(str(label_payload["kind"]))
    except ValueError as exc:
        msg = f"unsupported label kind: {label_payload['kind']!r}"
        raise PredictiveSpecError(msg) from exc


def _feature_columns(features: pl.DataFrame) -> tuple[str, ...]:
    columns = tuple(name for name in features.columns if name not in _MATRIX_METADATA_COLUMNS)
    if not columns:
        msg = "labelled matrix has no feature columns"
        raise PredictiveRunError(msg)
    return columns


def _train_and_test_rows(features: pl.DataFrame, fold_id: int) -> tuple[pl.DataFrame, pl.DataFrame]:
    fold_rows = features.filter(pl.col("fold_id") == fold_id)
    train_rows = fold_rows.filter(pl.col("fold_role") == FoldRole.TRAIN.value)
    test_rows = fold_rows.filter(pl.col("fold_role") == FoldRole.TEST.value)
    if train_rows.height == 0:
        msg = f"fold {fold_id} has no TRAIN rows"
        raise PredictiveRunError(msg)
    if test_rows.height == 0:
        msg = f"fold {fold_id} has no TEST rows"
        raise PredictiveRunError(msg)
    return train_rows, test_rows


def _fold_roles(rows: pl.DataFrame) -> tuple[FoldRole, ...]:
    roles: list[FoldRole] = []
    for value in rows.get_column("fold_role").to_list():
        roles.append(FoldRole(str(value)))
    return tuple(roles)


def _feature_matrix(rows: pl.DataFrame, feature_columns: tuple[str, ...]) -> np.ndarray:
    return rows.select(list(feature_columns)).to_numpy()


def _label_vector(rows: pl.DataFrame) -> np.ndarray:
    return np.asarray(rows.get_column("label").to_list(), dtype=np.float64)


def _positive_class_proba(proba: np.ndarray | None, *, n_rows: int) -> list[float | None]:
    if proba is None:
        return [None] * n_rows
    array = np.asarray(proba, dtype=np.float64)
    if array.ndim == 1:
        if array.shape[0] != n_rows:
            msg = f"predict_proba length {array.shape[0]} does not match TEST rows {n_rows}"
            raise PredictiveRunError(msg)
        return [float(value) for value in array.tolist()]
    if array.ndim != 2 or array.shape[0] != n_rows:
        msg = f"predict_proba shape {array.shape} does not match TEST rows {n_rows}"
        raise PredictiveRunError(msg)
    # Binary sklearn output is (n, 2) with classes sorted; last column is P(positive).
    column = array[:, -1]
    return [float(value) for value in column.tolist()]


def _relative_model_path(storage_root: Path, run_id: str, fold_id: int) -> str:
    run_dir = predictive_research_run_model_path(storage_root, run_id, fold_id)
    try:
        return run_dir.relative_to(storage_root).as_posix()
    except ValueError:
        return f"research/predictive_research/runs/{run_id}/models/fold_{fold_id}.bin"
