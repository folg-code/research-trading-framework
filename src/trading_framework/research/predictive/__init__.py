"""Predictive Research specification contracts and labelled feature-matrix builder."""

from trading_framework.research.predictive.errors import (
    PredictiveMatrixError,
    PredictiveSpecError,
)
from trading_framework.research.predictive.exclusions import MatrixExclusionCounts
from trading_framework.research.predictive.features import (
    FeatureMatrixSpec,
    FeatureSpec,
    FeatureTransform,
)
from trading_framework.research.predictive.labels import LabelKind, LabelSpec
from trading_framework.research.predictive.matrix import (
    LabelledFeatureMatrix,
    build_labelled_feature_matrix,
)
from trading_framework.research.predictive.spec import (
    PredictiveStudySpec,
    compute_definition_hash,
    load_predictive_study_spec,
    load_predictive_study_spec_from_dict,
)
from trading_framework.research.predictive.splitting import (
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
)

__all__ = [
    "FeatureMatrixSpec",
    "FeatureSpec",
    "FeatureTransform",
    "LabelKind",
    "LabelSpec",
    "LabelledFeatureMatrix",
    "MatrixExclusionCounts",
    "PredictiveMatrixError",
    "PredictiveSpecError",
    "PredictiveStudySpec",
    "PurgedWalkForwardSplitMode",
    "PurgedWalkForwardSplitSpec",
    "build_labelled_feature_matrix",
    "compute_definition_hash",
    "load_predictive_study_spec",
    "load_predictive_study_spec_from_dict",
]
