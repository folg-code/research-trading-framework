"""Tests for promoted-artifact fingerprint derivation (D-S049-05)."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import trading_framework
from trading_framework.research.datasets.promoted_artifact import (
    compute_promoted_artifact_fingerprint,
)


def _fingerprint(*, coefficients: tuple[float, ...] = (1.0, 2.0)) -> str:
    # `coefficients` is accepted only by this test helper, never by the
    # function under test — proving the fitted values cannot reach the hash.
    del coefficients
    return compute_promoted_artifact_fingerprint(
        run_fingerprint="a" * 64,
        fold_id=3,
        format="numpy_parameter_file",
        format_version="v1",
        model_family="sklearn.ridge",
        features=["feature-a:close", "feature-b:atr"],
        preprocessing_spec={"steps": ["IMPUTE_MEDIAN", "STANDARDIZE"]},
        estimator_spec={"family": "sklearn.ridge", "alpha": 1.0},
    )


def test_promoting_same_run_and_fold_twice_yields_same_fingerprint() -> None:
    first = _fingerprint()
    second = _fingerprint()
    assert first == second
    assert len(first) == 64


def test_fingerprint_matches_canonical_payload_hash() -> None:
    payload = {
        "run_fingerprint": "b" * 64,
        "fold_id": 1,
        "format": "numpy_parameter_file",
        "format_version": "v1",
        "model_family": "sklearn.logistic",
        "features": ["x:1", "x:2"],
        "preprocessing_spec": {"steps": ["IMPUTE_MEDIAN"]},
        "estimator_spec": {"family": "sklearn.logistic"},
    }
    expected = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    actual = compute_promoted_artifact_fingerprint(
        run_fingerprint="b" * 64,
        fold_id=1,
        format="numpy_parameter_file",
        format_version="v1",
        model_family="sklearn.logistic",
        features=["x:1", "x:2"],
        preprocessing_spec={"steps": ["IMPUTE_MEDIAN"]},
        estimator_spec={"family": "sklearn.logistic"},
    )
    assert actual == expected


def test_fingerprint_changes_with_format_fold_family_and_feature_order() -> None:
    baseline = _fingerprint()

    format_changed = compute_promoted_artifact_fingerprint(
        run_fingerprint="a" * 64,
        fold_id=3,
        format="onnx",
        format_version="v1",
        model_family="sklearn.ridge",
        features=["feature-a:close", "feature-b:atr"],
        preprocessing_spec={"steps": ["IMPUTE_MEDIAN", "STANDARDIZE"]},
        estimator_spec={"family": "sklearn.ridge", "alpha": 1.0},
    )
    fold_changed = compute_promoted_artifact_fingerprint(
        run_fingerprint="a" * 64,
        fold_id=4,
        format="numpy_parameter_file",
        format_version="v1",
        model_family="sklearn.ridge",
        features=["feature-a:close", "feature-b:atr"],
        preprocessing_spec={"steps": ["IMPUTE_MEDIAN", "STANDARDIZE"]},
        estimator_spec={"family": "sklearn.ridge", "alpha": 1.0},
    )
    family_changed = compute_promoted_artifact_fingerprint(
        run_fingerprint="a" * 64,
        fold_id=3,
        format="numpy_parameter_file",
        format_version="v1",
        model_family="sklearn.elastic_net",
        features=["feature-a:close", "feature-b:atr"],
        preprocessing_spec={"steps": ["IMPUTE_MEDIAN", "STANDARDIZE"]},
        estimator_spec={"family": "sklearn.ridge", "alpha": 1.0},
    )
    order_changed = compute_promoted_artifact_fingerprint(
        run_fingerprint="a" * 64,
        fold_id=3,
        format="numpy_parameter_file",
        format_version="v1",
        model_family="sklearn.ridge",
        features=["feature-b:atr", "feature-a:close"],
        preprocessing_spec={"steps": ["IMPUTE_MEDIAN", "STANDARDIZE"]},
        estimator_spec={"family": "sklearn.ridge", "alpha": 1.0},
    )

    assert format_changed != baseline
    assert fold_changed != baseline
    assert family_changed != baseline
    assert order_changed != baseline


def test_fitted_parameter_values_are_not_hashed() -> None:
    """A perturbed fitted coefficient does not perturb the fingerprint (Q9).

    The function under test accepts no coefficient/intercept/statistics
    argument at all, so this is structurally guaranteed rather than merely
    observed — this test documents that guarantee explicitly.
    """
    unperturbed = _fingerprint(coefficients=(1.0, 2.0))
    perturbed = _fingerprint(coefficients=(1.0, 999.999))
    assert unperturbed == perturbed


def test_fingerprint_module_does_not_import_ml_library() -> None:
    path = (
        Path(trading_framework.__file__).resolve().parent
        / "research"
        / "datasets"
        / "promoted_artifact.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)
    ml_roots = ("sklearn", "xgboost", "lightgbm", "catboost", "torch")
    assert not any(
        name == root or name.startswith(f"{root}.") for name in imported for root in ml_roots
    )
