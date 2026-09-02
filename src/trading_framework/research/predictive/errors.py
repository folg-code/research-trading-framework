"""Validation errors for Predictive Research specification contracts and builders."""

from trading_framework.core.exceptions import ValidationError


class PredictiveSpecError(ValidationError):
    """Raised when a predictive study, feature, label, or split spec is invalid."""


class PredictiveMatrixError(PredictiveSpecError):
    """Raised when a labelled feature matrix or fold assignment cannot be built."""


class PredictiveExtraError(ValidationError):
    """Raised when a requested estimator family requires an uninstalled extra.

    The message must name the extra (``ml``, ``ml-trees``, or ``dl``) and the requested family id.
    ``ImportError`` may be chained as ``__cause__`` but must not be the raised type.
    """


class PromotedArtifactFormatError(PredictiveSpecError):
    """Raised by ``load_promoted_artifact`` when it refuses a manifest/payload pair.

    Refusals (ADR-0029 §5), always raised **before** any arithmetic: an unknown
    ``format_version``, a ``model_family`` outside the evaluator's linear/
    logistic allow-list, a ``preprocessing_spec`` step the evaluator does not
    implement, or a feature-count mismatch between the manifest and the
    parameter payload. There is no bypass — no ``strict=False``, no
    ``allow_mismatch``, no environment variable — anywhere in
    ``load_promoted_artifact``'s API surface. The remedy for a refused load is
    re-promotion, never widening this guard.

    A difference in *training*-library version is deliberately **not** one of
    these refusals (ADR-0029 §5's relaxation): a parameter file has no
    coupling to scikit-learn, because scikit-learn is not involved in reading
    it. That version is enforced once, at *promotion* time, before any blob is
    unpickled — see ``infrastructure/ml/promotion.py`` (Sprint 049 T006b).
    """
