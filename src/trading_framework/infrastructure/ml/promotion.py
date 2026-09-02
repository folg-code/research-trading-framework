"""Promoted-artifact blob read + parameter extraction (ADR-0029 §4, §9).

This module, and only this module, performs the single narrow blob read that
ADR-0023 §7 was amended for (ADR-0029 §7): a one-time, promotion-time read of
a Predictive Research fold's fitted ``models/fold_{n}.bin`` blob
(``{"family", "estimator", "preprocessor"}`` written by
``FittedSklearnEstimator.serialize_artifact()``), from which it extracts
``coef_`` / ``intercept_`` and the fitted preprocessing statistics as plain
numbers — no library object leaves this module.

Two refusals live here, and only here:

- **The model-family allow-list.** Only ``sklearn.ridge`` / ``sklearn.elastic_net``
  / ``sklearn.logistic`` may be extracted. A tree or neural family is refused
  with :class:`PromotedFamilyUnsupportedError`, naming the family and stating
  the deferred joblib path is its future increment — not rejected forever.
- **The promotion-time scikit-learn version guard (D-S049-07).** Unpickling a
  joblib blob under a different scikit-learn version than wrote it is unsafe,
  so this guard runs *before* ``joblib.load`` — a pre-check on the run
  manifest's recorded ``library`` / ``library_version`` strings against the
  installed ``sklearn.__version__``, never a try/except around the unpickle.
  A mismatch raises :class:`PromotionVersionMismatchError`, whose message
  states that re-running the study is the remedy.

This is a **separate guard from ``load_promoted_artifact``'s** (ADR-0029 §5):
that one gates the promoted parameter file at *load* time and deliberately
does **not** check the training library version, because a parameter file has
no coupling to scikit-learn. This one gates the *blob* at *promotion* time,
before any unpickling, because a blob very much does.

Sklearn and joblib are imported lazily, inside function bodies only, never at
module level, so this module stays importable without the ``ml`` extra
installed (``infrastructure/ml/CLAUDE.md``). Extraction itself requires the
extra; the extraction functions are the only ones that touch it.
"""

from __future__ import annotations

import io
from typing import Any

import numpy as np

from trading_framework.research.datasets.promoted_artifact import MODEL_FAMILY_ALLOWLIST
from trading_framework.research.predictive.errors import PredictiveExtraError, PredictiveSpecError
from trading_framework.research.predictive.preprocessing import PreprocessingSpec
from trading_framework.research.predictive.promotion.parameters import PromotedArtifactParameters

_ML_EXTRA = "ml"
_REQUIRED_BLOB_KEYS = ("family", "estimator", "preprocessor")
_SUPPORTED_TRAINING_LIBRARY = "sklearn"


class PromotedFamilyUnsupportedError(PredictiveSpecError):
    """Raised when promotion is attempted for a family outside v1's allow-list.

    v1 covers ``sklearn.ridge`` / ``sklearn.elastic_net`` / ``sklearn.logistic``
    only (ADR-0029 §1). Tree (XGBoost/LightGBM/CatBoost) and neural (torch)
    families are **deferred**, not rejected forever — they need the
    version-pinned joblib path ADR-0029's Alternatives describes as the next
    increment once this mechanism is proven.
    """


class PromotionVersionMismatchError(PredictiveSpecError):
    """Raised before any unpickling when the installed sklearn version differs.

    Unpickling a joblib blob under a different scikit-learn version than wrote
    it is unsafe (ADR-0029 §4). The remedy is to re-run the study that
    produced the run being promoted — already-promoted artifacts are
    unaffected, because they carry no library coupling at all (ADR-0029 §5).
    """


def _import_sklearn() -> object:
    import sklearn

    return sklearn


def _import_joblib() -> object:
    import joblib

    return joblib


def require_promotion_sklearn_version(
    recorded_library: str,
    recorded_library_version: str,
) -> None:
    """Refuse promotion, before any unpickling, on a scikit-learn version mismatch.

    Compares the run manifest's recorded ``library`` / ``library_version``
    against the installed ``sklearn.__version__``. Only ``library == "sklearn"``
    is a version the guard knows how to certify safe to unpickle; anything
    else refuses outright, since v1 promotion supports sklearn families only.
    """
    try:
        sklearn = _import_sklearn()
    except ImportError as exc:
        msg = (
            f"promotion requires optional extra {_ML_EXTRA!r}; "
            f"install with `uv sync --extra {_ML_EXTRA}`"
        )
        raise PredictiveExtraError(msg) from exc

    installed_version = str(sklearn.__version__)  # type: ignore[attr-defined]
    if recorded_library != _SUPPORTED_TRAINING_LIBRARY:
        msg = (
            f"cannot promote a run trained with library {recorded_library!r}; "
            f"promotion only reads {_SUPPORTED_TRAINING_LIBRARY!r} blobs. "
            "Re-run the study with a supported estimator family."
        )
        raise PromotionVersionMismatchError(msg)
    if recorded_library_version != installed_version:
        msg = (
            f"cannot promote: the run was trained under {_SUPPORTED_TRAINING_LIBRARY} "
            f"{recorded_library_version!r}, but {installed_version!r} is installed. "
            "Unpickling a joblib blob under a different scikit-learn version than "
            "wrote it is unsafe. The remedy is to re-run the study under the "
            "installed scikit-learn version, then promote the new run."
        )
        raise PromotionVersionMismatchError(msg)


def require_supported_model_family(model_family: str) -> None:
    """Refuse a family outside v1's allow-list before touching any blob."""
    if model_family not in MODEL_FAMILY_ALLOWLIST:
        msg = (
            f"model family {model_family!r} is not supported for promotion; "
            f"v1 supports {sorted(MODEL_FAMILY_ALLOWLIST)} only. Tree and neural "
            "families are deferred to a future joblib-based promotion path, "
            "not rejected forever."
        )
        raise PromotedFamilyUnsupportedError(msg)


def extract_promoted_parameters(
    blob: bytes,
    *,
    model_family: str,
    recorded_library: str,
    recorded_library_version: str,
    preprocessing_spec: PreprocessingSpec,
) -> PromotedArtifactParameters:
    """Read a fitted-fold blob and extract plain-number promotion parameters.

    Order of operations, and each one is binding:

    1. Refuse a family outside the allow-list (:func:`require_supported_model_family`)
       — no blob touched.
    2. Refuse a scikit-learn version mismatch (:func:`require_promotion_sklearn_version`)
       — still before any unpickling.
    3. ``joblib.load`` the blob, requiring the ``{"family", "estimator",
       "preprocessor"}`` shape ``FittedSklearnEstimator.serialize_artifact()``
       writes.
    4. Assert the blob's own recorded family matches ``model_family`` (defence
       against a stale or corrupt manifest).
    5. Read ``coef_`` / ``intercept_`` off the fitted estimator.
    6. Wrap the fitted ``Pipeline`` back into ``FittedSklearnPreprocessor`` and
       call its existing ``statistics()`` — no statistics logic is
       reimplemented here.
    """
    require_supported_model_family(model_family)
    require_promotion_sklearn_version(recorded_library, recorded_library_version)

    payload = _load_blob_payload(blob)
    payload_family = str(payload["family"])
    if payload_family != model_family:
        msg = (
            f"promoted-artifact blob family {payload_family!r} does not match "
            f"the run manifest's declared family {model_family!r}"
        )
        raise PredictiveSpecError(msg)

    coefficients, intercept = _extract_linear_parameters(payload["estimator"], model_family)
    statistics = _read_preprocessing_statistics(payload["preprocessor"], preprocessing_spec)

    return PromotedArtifactParameters(
        coefficients=coefficients,
        intercept=intercept,
        impute_median=statistics.get("impute_median"),
        standardize_mean=statistics.get("standardize_mean"),
        standardize_scale=statistics.get("standardize_scale"),
    )


def _load_blob_payload(blob: bytes) -> dict[str, Any]:
    try:
        joblib = _import_joblib()
    except ImportError as exc:
        msg = (
            f"reading a promoted-run blob requires optional extra {_ML_EXTRA!r}; "
            f"install with `uv sync --extra {_ML_EXTRA}`"
        )
        raise PredictiveExtraError(msg) from exc

    payload = joblib.load(io.BytesIO(blob))  # type: ignore[attr-defined]
    if not isinstance(payload, dict):
        msg = f"promoted-run blob payload must be a mapping, got {type(payload).__name__}"
        raise PredictiveSpecError(msg)
    missing = [key for key in _REQUIRED_BLOB_KEYS if key not in payload]
    if missing:
        msg = f"promoted-run blob payload missing required key(s): {missing}"
        raise PredictiveSpecError(msg)
    return payload


def _extract_linear_parameters(
    estimator: Any, model_family: str
) -> tuple[tuple[float, ...], float]:
    coef = getattr(estimator, "coef_", None)
    intercept = getattr(estimator, "intercept_", None)
    if coef is None or intercept is None:
        msg = f"fitted estimator for family {model_family!r} has no coef_/intercept_"
        raise PredictiveSpecError(msg)

    coef_array = np.asarray(coef, dtype=np.float64).ravel()
    intercept_array = np.asarray(intercept, dtype=np.float64).ravel()
    if intercept_array.size != 1:
        msg = (
            f"fitted estimator for family {model_family!r} has a non-scalar intercept_ "
            f"of shape {np.asarray(intercept).shape}; only single-output models are supported"
        )
        raise PredictiveSpecError(msg)
    return tuple(float(value) for value in coef_array), float(intercept_array[0])


def _read_preprocessing_statistics(
    pipeline: Any,
    preprocessing_spec: PreprocessingSpec,
) -> dict[str, tuple[float, ...]]:
    from trading_framework.infrastructure.ml.sklearn.preprocessing import (
        FittedSklearnPreprocessor,
    )

    wrapped = FittedSklearnPreprocessor(spec=preprocessing_spec, _pipeline=pipeline)
    statistics = wrapped.statistics()
    return {key: tuple(values) for key, values in statistics.items()}
