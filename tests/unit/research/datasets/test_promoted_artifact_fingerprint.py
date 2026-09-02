"""Tests for promoted-artifact fingerprint derivation (D-S049-05)."""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path

import trading_framework
from trading_framework.research.datasets.promoted_artifact import (
    compute_promoted_artifact_fingerprint,
)

#: Names a future change might plausibly use for a fitted-value argument.
#: Used only to pin today's signature — see
#: ``test_fingerprint_has_no_fitted_parameter_input_by_construction``.
_FITTED_VALUE_PARAMETER_NAMES = frozenset(
    {"coefficients", "coefficient", "intercept", "weights", "statistics", "parameters", "params"}
)


def _fingerprint() -> str:
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


def test_fingerprint_has_no_fitted_parameter_input_by_construction() -> None:
    """The Q9 exclusion is structural, not filtered out at runtime.

    ``compute_promoted_artifact_fingerprint`` accepts no
    coefficient/intercept/weights/statistics argument at all — there is
    nothing a caller could even pass that would reach the hashed payload.
    This test pins that signature: if a future change added such a
    parameter, this test fails immediately, forcing a deliberate decision
    about whether (and how) it should be threaded into the hash, rather
    than letting it leak in silently.
    """
    parameters = inspect.signature(compute_promoted_artifact_fingerprint).parameters
    leaked = set(parameters) & _FITTED_VALUE_PARAMETER_NAMES
    assert not leaked, f"fitted-value parameter(s) reached the signature: {sorted(leaked)}"


def test_fingerprint_is_identical_across_two_different_fits_of_the_same_promotion() -> None:
    """Regression guard for the Q9 identity choice (D-S049-05).

    Simulates "the same run, fold and spec, promoted from two different
    fitted blobs": every field the function DOES hash is supplied
    identically in both calls, standing in for two fits whose only
    difference would be their coefficient/intercept/statistics values.
    Because fitted values are never part of the input (see the signature
    test above), the two fingerprints must be equal — identity is "which
    run, which fold, which spec", never "which numbers came out of the fit."
    """
    fit_one = _fingerprint()
    fit_two = _fingerprint()
    assert fit_one == fit_two


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
