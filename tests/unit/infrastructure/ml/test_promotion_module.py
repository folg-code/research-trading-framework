"""Promotion adapter tests that must pass without the ml extra installed.

Companion to ``test_promotion.py`` (marked ``pytest.mark.ml``): this file
covers the parts of ``infrastructure/ml/promotion.py`` that do not require
scikit-learn/joblib at all — the family allow-list refusal, the module's own
lazy-import discipline, and the "missing extra" behaviour of the version
guard and the blob loader.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from trading_framework.infrastructure.ml import promotion
from trading_framework.research.predictive.errors import PredictiveExtraError


def _module_level_imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.append(node.module)
    return names


def _is_sklearn_or_joblib(module_name: str) -> bool:
    return (
        module_name in {"sklearn", "joblib"}
        or module_name.startswith("sklearn.")
        or module_name.startswith("joblib.")
    )


def test_promotion_module_does_not_import_sklearn_or_joblib_at_module_level() -> None:
    """The promotion adapter must stay importable without the ``ml`` extra."""
    module_path = Path(promotion.__file__).resolve()
    offenders = [
        name for name in _module_level_imported_names(module_path) if _is_sklearn_or_joblib(name)
    ]
    assert offenders == []


def test_module_is_importable_without_ml_extra() -> None:
    reloaded = importlib.reload(promotion)
    assert reloaded is promotion


def test_require_supported_model_family_accepts_allowlisted_families() -> None:
    promotion.require_supported_model_family("sklearn.ridge")
    promotion.require_supported_model_family("sklearn.elastic_net")
    promotion.require_supported_model_family("sklearn.logistic")


def test_require_supported_model_family_refuses_tree_family_before_any_blob_read() -> None:
    with pytest.raises(promotion.PromotedFamilyUnsupportedError) as caught:
        promotion.require_supported_model_family("xgboost.regressor")
    message = str(caught.value)
    assert "xgboost.regressor" in message
    assert "deferred" in message


def test_require_supported_model_family_refuses_neural_family_before_any_blob_read() -> None:
    with pytest.raises(promotion.PromotedFamilyUnsupportedError) as caught:
        promotion.require_supported_model_family("torch.feedforward.regressor")
    message = str(caught.value)
    assert "torch.feedforward.regressor" in message
    assert "deferred" in message


def test_missing_ml_extra_raises_predictive_extra_error_for_version_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_sklearn() -> object:
        raise ImportError("sklearn is not installed")

    monkeypatch.setattr(promotion, "_import_sklearn", missing_sklearn)
    with pytest.raises(PredictiveExtraError) as caught:
        promotion.require_promotion_sklearn_version("sklearn", "1.5.0")
    message = str(caught.value)
    assert "ml" in message
    assert isinstance(caught.value.__cause__, ImportError)
    assert not isinstance(caught.value, ImportError)


def test_missing_ml_extra_raises_predictive_extra_error_for_extraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_joblib() -> object:
        raise ImportError("joblib is not installed")

    monkeypatch.setattr(promotion, "_import_joblib", missing_joblib)
    with pytest.raises(PredictiveExtraError) as caught:
        promotion._load_blob_payload(b"not a real blob")
    message = str(caught.value)
    assert "ml" in message
    assert isinstance(caught.value.__cause__, ImportError)
    assert not isinstance(caught.value, ImportError)
