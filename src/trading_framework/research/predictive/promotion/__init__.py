"""Pure-NumPy promoted-artifact evaluator (ADR-0029 §1, §9).

Domain-layer subpackage: NumPy only, never sklearn / xgboost / lightgbm /
catboost / torch. ``infrastructure/ml/promotion.py`` is the only place that
touches scikit-learn (behind lazy imports); this subpackage is what
Sprint 050's Market Analysis component must be able to reach without pulling
in any ML library.

``FittedNumpyPreprocessor`` / ``fit_numpy_preprocessor`` (Sprint 043,
D-S043-15) live here as of the Sprint 049 Q8 move — they used to live in
``infrastructure/ml/torch/preprocessing.py``. The torch adapter imports them
downward from here.
"""

from trading_framework.research.predictive.promotion.evaluator import (
    PromotedManifestLike,
    PromotedPredictor,
    load_promoted_artifact,
)
from trading_framework.research.predictive.promotion.parameters import (
    PROMOTED_ARTIFACT_FORMAT,
    SUPPORTED_FORMAT_VERSIONS,
    PromotedArtifactParameters,
)
from trading_framework.research.predictive.promotion.preprocessing import (
    FittedNumpyPreprocessor,
    as_feature_matrix,
    as_sequence_windows,
    fit_numpy_preprocessor,
    transform_windows,
)

__all__ = [
    "PROMOTED_ARTIFACT_FORMAT",
    "SUPPORTED_FORMAT_VERSIONS",
    "FittedNumpyPreprocessor",
    "PromotedArtifactParameters",
    "PromotedManifestLike",
    "PromotedPredictor",
    "as_feature_matrix",
    "as_sequence_windows",
    "fit_numpy_preprocessor",
    "load_promoted_artifact",
    "transform_windows",
]
