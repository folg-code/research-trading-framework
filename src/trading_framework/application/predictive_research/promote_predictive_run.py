"""Promote an existing Predictive Research run into a promoted artifact.

Orchestration only (ADR-0029 §9): this module selects the last walk-forward
fold, runs the two promotion-time guards, performs the one narrow blob read
ADR-0023 §7 was amended for (via ``infrastructure.ml.promotion``, which owns
the actual extraction), computes the artifact fingerprint, and writes the
content-addressed store directory. No parameter-extraction or evaluation
logic is reimplemented here.

**Order of operations, and each one is binding** (mirrors D-S049-14 /
ADR-0029 §4, and T006b's own order docstring):

1. Read the run envelope (:class:`PredictiveRunRepository.read`) — this
   already refuses an unsupported run manifest schema version, before any
   other work.
2. Refuse a ``model_family`` outside the linear/logistic allow-list
   (:func:`require_supported_model_family`) — before touching any blob.
3. Refuse a promotion-time scikit-learn version mismatch
   (:func:`require_promotion_sklearn_version`) — still before any unpickling.
4. Select the **last** walk-forward fold — the highest ``fold_id`` the run
   actually persisted a model blob for (D-S049-04).
5. Read the associated dataset envelope to recover the ordered feature
   identity list positionally matching the labelled matrix's feature
   columns — the same columns the run fit against (D-S049-05).
6. Read that one fold's blob and extract plain-number parameters
   (:func:`extract_promoted_parameters`) — the single narrow blob read
   ADR-0023 §7 is amended for.
7. Compute the artifact fingerprint and write the store directory. Any
   refusal above happens before this step, so a refused promotion writes
   nothing (D-S049-03).

The source run directory is never written to by this workflow.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from trading_framework.infrastructure.ml.promotion import (
    extract_promoted_parameters,
    require_promotion_sklearn_version,
    require_supported_model_family,
)
from trading_framework.infrastructure.storage.paths import (
    predictive_research_run_model_path,
    promoted_artifact_dir,
)
from trading_framework.research.datasets.predictive import (
    PredictiveDatasetEnvelope,
    PredictiveDatasetRef,
    PredictiveDatasetRepository,
)
from trading_framework.research.datasets.predictive_run import (
    PredictiveRunManifest,
    PredictiveRunRef,
    PredictiveRunRepository,
)
from trading_framework.research.datasets.promoted_artifact import (
    PROMOTED_ARTIFACT_SCHEMA_VERSION,
    PromotedArtifactManifest,
    PromotedArtifactRef,
    PromotedArtifactRepository,
    compute_promoted_artifact_fingerprint,
)
from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.features import FeatureMatrixSpec, FeatureSpec
from trading_framework.research.predictive.preprocessing import PreprocessingSpec
from trading_framework.research.predictive.promotion.parameters import PROMOTED_ARTIFACT_FORMAT
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock

#: The only format_version this workflow writes (mirrors
#: ``research.predictive.promotion.parameters.SUPPORTED_FORMAT_VERSIONS``,
#: which the *load* side enforces; this is the *write* side's single choice).
_PROMOTED_ARTIFACT_FORMAT_VERSION = "v1"

#: The labelled-matrix metadata-column contract. Duplicated here (rather than
#: importing the private ``_MATRIX_METADATA_COLUMNS`` /
#: ``_REQUIRED_FEATURE_COLUMNS`` constants from
#: ``application.predictive_research.run_predictive_research`` /
#: ``research.datasets.predictive``) for the same reason
#: ``MODEL_FAMILY_ALLOWLIST`` is duplicated between ``research.datasets`` and
#: ``research.predictive.promotion.evaluator`` — both are private to their
#: module, and this is the same small, stable contract, not a design decision.
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


class PromotePredictiveRunError(PredictiveSpecError):
    """Raised when ``promote_predictive_run`` cannot promote the requested run.

    Covers workflow-level problems that are not one of the two named guards
    (family allow-list, promotion-time version guard) — a run with no
    persisted model blobs, or a dataset whose ``study_spec`` does not declare
    the ordered feature list promotion needs.
    """


@dataclass(frozen=True, slots=True)
class PromotePredictiveRunRequest:
    """Input for one promotion of an existing Predictive Research run."""

    run_ref: PredictiveRunRef
    storage_root: Path
    clock: Clock | None = None
    run_repository: PredictiveRunRepository | None = None
    dataset_repository: PredictiveDatasetRepository | None = None
    promoted_repository: PromotedArtifactRepository | None = None


@dataclass(frozen=True, slots=True)
class PromotePredictiveRunResult:
    """Outcome of one promotion.

    Fields are plain primitives (not domain types) so callers — including
    ``apps/cli`` — never need to import ``research.datasets.promoted_artifact``
    just to report the result.
    """

    artifact_fingerprint: str
    directory: Path
    fold_id: int


def promote_predictive_run(request: PromotePredictiveRunRequest) -> PromotePredictiveRunResult:
    """Promote the last walk-forward fold of an existing run into a promoted artifact.

    Refuses an unsupported run-manifest schema version, a ``model_family``
    outside v1's allow-list, or a promotion-time scikit-learn version
    mismatch — in that order, all before any blob is read and all before the
    promoted store directory is written (D-S049-03, ADR-0029 §4). Never
    mutates the source run directory.
    """
    run_repository = request.run_repository or PredictiveRunRepository(request.storage_root)
    # Refuses an unsupported PredictiveRunManifest schema version before any
    # other work (PredictiveRunRepository.read's own guard).
    run_envelope = run_repository.read(request.run_ref)
    manifest = run_envelope.manifest

    model_family = str(manifest.estimator_spec.get("family", ""))
    require_supported_model_family(model_family)
    require_promotion_sklearn_version(manifest.library, manifest.library_version)

    fold_id = _select_last_fold(manifest)

    dataset_repository = request.dataset_repository or PredictiveDatasetRepository(
        request.storage_root
    )
    dataset_envelope = dataset_repository.read(PredictiveDatasetRef(dataset_id=manifest.dataset_id))
    feature_identities = _ordered_feature_identities(dataset_envelope)

    preprocessing_spec = PreprocessingSpec.from_dict(manifest.preprocessing_spec)

    blob_path = predictive_research_run_model_path(request.storage_root, manifest.run_id, fold_id)
    if not blob_path.exists():
        msg = f"missing model blob for promoted fold {fold_id}: {blob_path}"
        raise PromotePredictiveRunError(msg)
    blob = blob_path.read_bytes()

    parameters = extract_promoted_parameters(
        blob,
        model_family=model_family,
        recorded_library=manifest.library,
        recorded_library_version=manifest.library_version,
        preprocessing_spec=preprocessing_spec,
    )

    artifact_fingerprint = compute_promoted_artifact_fingerprint(
        run_fingerprint=manifest.run_fingerprint,
        fold_id=fold_id,
        format=PROMOTED_ARTIFACT_FORMAT,
        format_version=_PROMOTED_ARTIFACT_FORMAT_VERSION,
        model_family=model_family,
        features=feature_identities,
        preprocessing_spec=manifest.preprocessing_spec,
        estimator_spec=manifest.estimator_spec,
    )

    clock = request.clock or SystemClock()
    promoted_manifest = PromotedArtifactManifest(
        schema_version=PROMOTED_ARTIFACT_SCHEMA_VERSION,
        artifact_fingerprint=artifact_fingerprint,
        run_fingerprint=manifest.run_fingerprint,
        dataset_fingerprint=manifest.dataset_fingerprint,
        fold_id=fold_id,
        feature_output_refs=feature_identities,
        model_family=model_family,
        format=PROMOTED_ARTIFACT_FORMAT,
        format_version=_PROMOTED_ARTIFACT_FORMAT_VERSION,
        preprocessing_spec=dict(manifest.preprocessing_spec),
        estimator_spec=dict(manifest.estimator_spec),
        training_library=manifest.library,
        training_library_version=manifest.library_version,
        created_at_utc=clock.now(),
    )

    promoted_repository = request.promoted_repository or PromotedArtifactRepository(
        request.storage_root
    )
    artifact_ref: PromotedArtifactRef = promoted_repository.write(
        promoted_manifest, artifact_payload=parameters.to_dict()
    )

    directory = promoted_artifact_dir(request.storage_root, artifact_fingerprint)
    return PromotePredictiveRunResult(
        artifact_fingerprint=artifact_ref.artifact_fingerprint,
        directory=directory,
        fold_id=fold_id,
    )


def _select_last_fold(manifest: PredictiveRunManifest) -> int:
    """Return the highest ``fold_id`` the run persisted a model blob for.

    The last walk-forward fold is the one fitted on the most recent
    available TRAIN span (D-S049-04) — for an expanding/rolling walk-forward
    split, that is the highest ``fold_id`` among the folds the run actually
    fit and persisted a blob for.
    """
    if not manifest.model_files:
        msg = f"run {manifest.run_id!r} has no persisted model files to promote"
        raise PromotePredictiveRunError(msg)
    return max(int(key) for key in manifest.model_files)


def _ordered_feature_identities(envelope: PredictiveDatasetEnvelope) -> tuple[str, ...]:
    """Return per-feature identity strings, in the model's positional column order.

    Column order comes from the dataset's persisted feature matrix (the same
    columns ``run_predictive_research`` selected positionally when fitting),
    not from the declaration order in ``study_spec`` — the two must agree,
    but the matrix's order is what the fitted coefficients actually index
    into. Each identity string is a canonical-JSON encoding of the declared
    ``FeatureSpec`` (component, parameters, output, alias): the *declared*
    feature identity, not a fully resolved ``OutputRef`` — resolving one
    would require re-running analysis assembly, which promotion does not do
    (D-S049-14 / "no change to the Phase 10 run pipeline").
    """
    feature_columns = _feature_columns(envelope.features)
    raw_features = envelope.manifest.study_spec.get("features")
    if raw_features is None:
        msg = (
            f"dataset {envelope.manifest.dataset_id!r} study_spec has no declared "
            "'features'; promotion needs the ordered feature identity list to "
            "build the promoted artifact manifest"
        )
        raise PromotePredictiveRunError(msg)
    try:
        declared = FeatureMatrixSpec.from_dict(raw_features)
    except PredictiveSpecError as exc:
        msg = f"dataset {envelope.manifest.dataset_id!r} study_spec features are invalid: {exc}"
        raise PromotePredictiveRunError(msg) from exc

    by_alias = {feature.alias: _feature_identity(feature) for feature in declared.features}
    missing = [column for column in feature_columns if column not in by_alias]
    if missing:
        msg = (
            f"dataset {envelope.manifest.dataset_id!r} study_spec is missing declared "
            f"feature(s) used by the fitted matrix: {missing}"
        )
        raise PromotePredictiveRunError(msg)
    return tuple(by_alias[column] for column in feature_columns)


def _feature_identity(feature: FeatureSpec) -> str:
    return json.dumps(feature.to_dict(), sort_keys=True, separators=(",", ":"))


def _feature_columns(features: pl.DataFrame) -> tuple[str, ...]:
    return tuple(name for name in features.columns if name not in _MATRIX_METADATA_COLUMNS)
