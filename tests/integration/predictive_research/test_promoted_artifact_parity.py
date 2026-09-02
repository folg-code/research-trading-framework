"""Path A parity replay (S049-T010b): NumPy evaluator vs sklearn (Comparison 2).

ADR-0029 Section 6 / D-S049-06 names TWO structurally different parity
comparisons and locks the bar for exactly one of them here:

    Comparison 1 (offline vs online, Sprint 050's release gate) is NOT this
    test -- it stays exact, unconditionally, and is out of scope for Sprint 049.

    Comparison 2 (NumPy evaluator vs sklearn's own ``predictions.parquet``)
    IS this test. It trains a ridge and a logistic model on the synthetic
    D-S039-CI-dataset fixture (``_fixtures.py``), promotes each run's last
    fold, loads the promoted artifact with the pure-NumPy evaluator, and
    re-predicts the run's own TEST rows. The bar table is implemented
    literally:

        y_pred                          ridge, elastic_net   exact (==)
        y_pred (class label)            logistic             exact (==)
        decision function z = Xw + b    logistic              exact (==), asserted
                                                               separately from y_proba
        y_proba                         logistic              rtol=0, atol=1e-15,
                                                               and ONLY here

The oracle for ``y_pred`` / ``y_proba`` is the run's own persisted
``predictions.parquet`` -- never a hand-copied constant (D-S049-06). The
oracle for the logistic decision function ``z`` is scikit-learn's own
``decision_function()``, read directly off the fold's fitted blob (the one
narrow blob read this suite performs, mirroring ADR-0029 Section 7's own
promotion-time read) -- ``predictions.parquet`` does not carry ``z``, so
comparing against it independently is the only way Comparison 2's ``z`` bar
can be checked at all, and it keeps that comparison honestly library-vs-library
rather than evaluator-vs-itself.

Every assertion runs through ``_assert_exact`` / ``_assert_proba_tolerance``,
which the mutation-check tests below reuse against a deliberately perturbed
artifact and assert *fail* -- proving these assertions have teeth (the
lesson from PR #389's vacuous fingerprint-mutation test earlier in this
sprint: perturbing a value that is never fed into the comparison proves
nothing). This was additionally verified by hand: temporarily perturbing the
evaluator's own linear-output and decision-function arithmetic in
``research/predictive/promotion/evaluator.py`` and re-running this file made
the genuine (non-mutation-check) tests above fail, before the change was
reverted -- see the PR description for the exact diffs exercised.
"""

from __future__ import annotations

import io
from dataclasses import replace
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from tests.integration.predictive_research._fixtures import (
    FEATURE_COLUMNS,
    promote,
    read_promoted,
    run_fixture,
)
from trading_framework.application.predictive_research.run_predictive_research import (
    RunPredictiveResearchResult,
)
from trading_framework.infrastructure.storage.paths import predictive_research_run_model_path
from trading_framework.research.datasets.predictive import (
    PredictiveDatasetRef,
    PredictiveDatasetRepository,
)
from trading_framework.research.predictive import TaskType
from trading_framework.research.predictive.promotion.evaluator import load_promoted_artifact

pytest.importorskip("sklearn")

pytestmark = pytest.mark.ml

#: The locked ceiling for the ONE tolerated column in Comparison 2
#: (ADR-0029 §6 / D-S049-06). Widening this is a STOP-and-ask, never a
#: silent edit -- see the module docstring.
_Y_PROBA_CEILING = 1e-15


def _last_fold_test_frame(
    storage_root: Path,
    run_result: RunPredictiveResearchResult,
    fold_id: int,
) -> tuple[np.ndarray, pl.DataFrame]:
    """Return (feature matrix, predictions) for the promoted fold's TEST rows.

    Joined by (entity_id, fold_id), sorted deterministically, with an
    equal-height assertion so a join that silently dropped rows -- or
    matched nothing at all -- cannot pass vacuously (D-S049-06).
    """
    dataset_repository = PredictiveDatasetRepository(storage_root)
    dataset_ref = PredictiveDatasetRef(dataset_id=run_result.envelope.manifest.dataset_id)
    dataset_envelope = dataset_repository.read(dataset_ref)

    dataset_test_rows = dataset_envelope.features.filter(
        (pl.col("fold_id") == fold_id) & (pl.col("fold_role") == "TEST")
    ).sort("entity_id")
    predictions = run_result.envelope.predictions.filter(pl.col("fold_id") == fold_id).sort(
        "entity_id"
    )
    assert dataset_test_rows.height > 0, "fixture produced no TEST rows for the promoted fold"
    assert dataset_test_rows.height == predictions.height, (
        "dataset TEST rows and predictions.parquet TEST rows for the promoted fold "
        "do not have the same row count -- the join would be vacuous"
    )
    assert (
        dataset_test_rows.get_column("entity_id").to_list()
        == predictions.get_column("entity_id").to_list()
    )

    features = dataset_test_rows.select(list(FEATURE_COLUMNS)).to_numpy()
    return features, predictions


def _sklearn_decision_function(
    storage_root: Path,
    run_id: str,
    fold_id: int,
    features: np.ndarray,
) -> np.ndarray:
    """The Comparison-2 oracle for ``z`` -- scikit-learn's own decision_function.

    ``predictions.parquet`` never carries the raw decision function, only
    ``y_pred`` / ``y_proba``, so this is the one place this suite reads the
    fold's fitted blob directly (mirroring the single narrow read ADR-0029
    §7 permits at promotion time) -- necessary to keep the ``z`` bar an
    honest NumPy-vs-sklearn comparison rather than the evaluator checked
    against itself.
    """
    import joblib

    blob_path = predictive_research_run_model_path(storage_root, run_id, fold_id)
    payload = joblib.load(io.BytesIO(blob_path.read_bytes()))
    preprocessed = payload["preprocessor"].transform(features)
    return np.asarray(payload["estimator"].decision_function(preprocessed), dtype=np.float64)


def _assert_exact(actual: np.ndarray, expected: np.ndarray, *, label: str) -> None:
    np.testing.assert_array_equal(actual, expected, err_msg=f"{label} is not bitwise exact")


def _assert_proba_tolerance(actual: np.ndarray, expected: np.ndarray) -> float:
    """Assert the locked ``y_proba`` bar and return the observed max deviation."""
    deviation = float(np.max(np.abs(actual - expected)))
    assert deviation <= _Y_PROBA_CEILING, (
        f"y_proba max observed deviation {deviation!r} exceeds the ADR-0029 §6 ceiling "
        f"of {_Y_PROBA_CEILING!r} -- this is a PARITY DEFECT (STOP-and-report), never a "
        "reason to widen the tolerance."
    )
    np.testing.assert_allclose(actual, expected, rtol=0, atol=_Y_PROBA_CEILING)
    return deviation


# --------------------------------------------------------------------------
# Ridge (regression): y_pred exact, no decision function / probability bar.
# --------------------------------------------------------------------------


def test_ridge_promoted_artifact_reproduces_run_predictions_exactly(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    run_result = run_fixture(
        storage_root,
        mode="regression",
        label_kind="REGRESSION",
        family="sklearn.ridge",
        task_type=TaskType.REGRESSION,
        dataset_id="aaaabbbbccccddd1",
    )
    artifact_ref = promote(storage_root, run_result)
    manifest, payload = read_promoted(storage_root, artifact_ref)

    features, predictions = _last_fold_test_frame(storage_root, run_result, manifest.fold_id)
    predictor = load_promoted_artifact(manifest, payload)

    y_pred = predictor.predict(features)
    y_pred_oracle = predictions.get_column("y_pred").to_numpy()
    _assert_exact(y_pred, y_pred_oracle, label="y_pred (sklearn.ridge)")


# --------------------------------------------------------------------------
# Logistic (classification): all four D-S049-06 bars.
# --------------------------------------------------------------------------


def test_logistic_promoted_artifact_reproduces_run_predictions_at_locked_bars(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "workspace"
    run_result = run_fixture(
        storage_root,
        mode="binary",
        label_kind="BINARY",
        family="sklearn.logistic",
        task_type=TaskType.CLASSIFICATION,
        dataset_id="bbbbccccddddeee1",
    )
    artifact_ref = promote(storage_root, run_result)
    manifest, payload = read_promoted(storage_root, artifact_ref)

    features, predictions = _last_fold_test_frame(storage_root, run_result, manifest.fold_id)
    predictor = load_promoted_artifact(manifest, payload)
    assert hasattr(predictor, "decision_function")
    assert hasattr(predictor, "predict_proba")

    y_pred = predictor.predict(features)
    y_pred_oracle = predictions.get_column("y_pred").to_numpy()
    _assert_exact(y_pred, y_pred_oracle, label="y_pred (sklearn.logistic)")

    z = predictor.decision_function(features)
    z_oracle = _sklearn_decision_function(
        storage_root, run_result.run_id, manifest.fold_id, features
    )
    _assert_exact(z, z_oracle, label="decision function z (sklearn.logistic)")

    y_proba = predictor.predict_proba(features)
    y_proba_oracle = predictions.get_column("y_proba").to_numpy()
    deviation = _assert_proba_tolerance(y_proba, y_proba_oracle)
    # Recorded here (test output) for the sprint Review's measured-deviation
    # entry (ADR-0029 Follow-up / SPRINT_049 T014) -- never used to justify
    # widening the ceiling asserted above.
    print(f"[T010b] observed max y_proba deviation (sklearn.logistic): {deviation!r}")


# --------------------------------------------------------------------------
# Mutation checks: a perturbed coefficient must make the SAME assertion
# helpers the passing tests use actually fail (not a hand-rolled inequality
# disconnected from the real comparison path -- see the module docstring).
# --------------------------------------------------------------------------


def test_mutation_check_perturbed_ridge_coefficient_fails_parity_assertion(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "workspace"
    run_result = run_fixture(
        storage_root,
        mode="regression",
        label_kind="REGRESSION",
        family="sklearn.ridge",
        task_type=TaskType.REGRESSION,
        dataset_id="ccccddddeeeeff1",
    )
    artifact_ref = promote(storage_root, run_result)
    manifest, payload = read_promoted(storage_root, artifact_ref)
    features, predictions = _last_fold_test_frame(storage_root, run_result, manifest.fold_id)
    y_pred_oracle = predictions.get_column("y_pred").to_numpy()

    genuine_predictor = load_promoted_artifact(manifest, payload)
    _assert_exact(
        genuine_predictor.predict(features), y_pred_oracle, label="y_pred (sanity, unperturbed)"
    )

    perturbed_coefficients = (payload.coefficients[0] + 1.0, *payload.coefficients[1:])
    perturbed_payload = replace(payload, coefficients=perturbed_coefficients)
    perturbed_predictor = load_promoted_artifact(manifest, perturbed_payload)

    with pytest.raises(AssertionError):
        _assert_exact(
            perturbed_predictor.predict(features), y_pred_oracle, label="y_pred (mutated)"
        )


def test_mutation_check_perturbed_logistic_coefficient_fails_parity_assertion(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "workspace"
    run_result = run_fixture(
        storage_root,
        mode="binary",
        label_kind="BINARY",
        family="sklearn.logistic",
        task_type=TaskType.CLASSIFICATION,
        dataset_id="ddddeeeeffff0001",
    )
    artifact_ref = promote(storage_root, run_result)
    manifest, payload = read_promoted(storage_root, artifact_ref)
    features, predictions = _last_fold_test_frame(storage_root, run_result, manifest.fold_id)
    y_proba_oracle = predictions.get_column("y_proba").to_numpy()

    genuine_predictor = load_promoted_artifact(manifest, payload)
    assert hasattr(genuine_predictor, "predict_proba")
    _assert_proba_tolerance(
        genuine_predictor.predict_proba(features),
        y_proba_oracle,
    )

    perturbed_coefficients = (payload.coefficients[0] + 1.0, *payload.coefficients[1:])
    perturbed_payload = replace(payload, coefficients=perturbed_coefficients)
    perturbed_predictor = load_promoted_artifact(manifest, perturbed_payload)
    assert hasattr(perturbed_predictor, "predict_proba")

    with pytest.raises(AssertionError):
        _assert_proba_tolerance(
            perturbed_predictor.predict_proba(features),
            y_proba_oracle,
        )
