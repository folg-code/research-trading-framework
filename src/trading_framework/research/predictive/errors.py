"""Validation errors for Predictive Research specification contracts and builders."""

from trading_framework.core.exceptions import ValidationError


class PredictiveSpecError(ValidationError):
    """Raised when a predictive study, feature, label, or split spec is invalid."""


class PredictiveMatrixError(PredictiveSpecError):
    """Raised when a labelled feature matrix or fold assignment cannot be built."""


class ReservedSampleKindError(PredictiveSpecError):
    """Raised when a ``SampleSpec.kind`` names a reserved, not-yet-implemented kind.

    Covers ``strategy_trades``, ``labelled_setups`` and ``sessions_or_windows``
    (ADR-0031 §1, D-S056-04). The message names the increment that owns the
    kind (``16F`` or ``later, unassigned``). Never a silently-accepted no-op.
    """


class ReservedPredictiveTaskError(PredictiveSpecError):
    """Raised when a ``PredictiveTask`` names a reserved, not-yet-implemented task.

    Covers ``TRADE_OUTCOME``, ``NO_TRADE_FILTER``, ``REGIME_CLASSIFICATION``,
    ``VOLATILITY_FORECAST`` and ``DISCRETIONARY_SETUP_CLASSIFICATION``
    (ADR-0031 §5, D-S056-09). The message names the owning increment. Never a
    silently-accepted no-op.
    """


class IncompatibleSampleTaskError(PredictiveSpecError):
    """Raised when a ``SampleSpec.kind`` / ``PredictiveTask`` pairing is refused.

    ADR-0031 §5's compatibility matrix accepts exactly three pairings; anything
    else — most notably ``every_bar`` + ``SIGNAL_QUALITY``, where there is no
    signal whose quality could be judged — is refused here.
    """


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
