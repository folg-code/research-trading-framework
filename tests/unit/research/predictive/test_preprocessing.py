"""Unit tests for the fold-local preprocessing spec contract."""

from __future__ import annotations

import json

import pytest

from trading_framework.research.predictive import (
    FoldRole,
    PredictiveSpecError,
    PreprocessingSpec,
    PreprocessingStep,
    canonicalize_preprocessing_json,
    default_preprocessing_spec,
    require_train_only_fit_roles,
)


def test_default_preprocessing_is_impute_then_standardize() -> None:
    spec = default_preprocessing_spec()
    assert spec.steps == (PreprocessingStep.IMPUTE_MEDIAN, PreprocessingStep.STANDARDIZE)


def test_preprocessing_spec_default_factory_matches_documented_pipeline() -> None:
    spec = PreprocessingSpec()
    assert spec.to_dict() == {"steps": ["IMPUTE_MEDIAN", "STANDARDIZE"]}


def test_preprocessing_identity_is_json_stable() -> None:
    spec = PreprocessingSpec()
    canonical = canonicalize_preprocessing_json(spec)
    assert canonical == json.dumps(spec.identity_payload(), sort_keys=True, separators=(",", ":"))
    assert json.loads(canonical) == {"steps": ["IMPUTE_MEDIAN", "STANDARDIZE"]}


def test_preprocessing_spec_round_trip() -> None:
    spec = PreprocessingSpec(steps=(PreprocessingStep.STANDARDIZE,))
    restored = PreprocessingSpec.from_dict(spec.to_dict())
    assert restored == spec


def test_preprocessing_spec_rejects_empty_steps() -> None:
    with pytest.raises(PredictiveSpecError, match="at least one step"):
        PreprocessingSpec(steps=())


def test_preprocessing_spec_rejects_duplicate_steps() -> None:
    with pytest.raises(PredictiveSpecError, match="unique"):
        PreprocessingSpec(steps=(PreprocessingStep.STANDARDIZE, PreprocessingStep.STANDARDIZE))


def test_preprocessing_spec_rejects_unknown_step() -> None:
    with pytest.raises(PredictiveSpecError, match="invalid preprocessing step"):
        PreprocessingSpec.from_dict({"steps": ["PCA"]})


def test_fit_roles_accept_train_only() -> None:
    require_train_only_fit_roles((FoldRole.TRAIN, FoldRole.TRAIN))


@pytest.mark.parametrize(
    "role",
    [FoldRole.TEST, FoldRole.PURGED, FoldRole.EMBARGOED],
)
def test_fit_roles_reject_non_train(role: FoldRole) -> None:
    with pytest.raises(PredictiveSpecError, match="TRAIN rows only"):
        require_train_only_fit_roles((FoldRole.TRAIN, role))


def test_fit_roles_reject_purged_and_embargoed_even_without_train() -> None:
    with pytest.raises(PredictiveSpecError, match="PURGED and EMBARGOED"):
        require_train_only_fit_roles((FoldRole.PURGED, FoldRole.EMBARGOED))


def test_fit_roles_reject_empty() -> None:
    with pytest.raises(PredictiveSpecError, match="at least one TRAIN row"):
        require_train_only_fit_roles(())


def test_preprocessing_spec_is_shared_identity_not_fitted_state() -> None:
    """The hashed spec is fold-independent; fitted statistics are not.

    Two folds share one PreprocessingSpec identity. Fit remains TRAIN-only and
    per-fold: a pipeline fitted on fold 1 TRAIN must not be reused on fold 2.
    """
    fold_1_spec = default_preprocessing_spec()
    fold_2_spec = default_preprocessing_spec()
    assert canonicalize_preprocessing_json(fold_1_spec) == canonicalize_preprocessing_json(
        fold_2_spec
    )
    require_train_only_fit_roles((FoldRole.TRAIN,))
