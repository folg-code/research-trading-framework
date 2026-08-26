"""Predictive Research specification contracts, labelled matrix, and fold planner."""

from trading_framework.research.predictive.errors import (
    PredictiveExtraError,
    PredictiveMatrixError,
    PredictiveSpecError,
)
from trading_framework.research.predictive.estimators import (
    EstimatorDescription,
    EstimatorSpec,
    FittedPredictiveEstimator,
    PredictiveEstimator,
    TaskType,
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
from trading_framework.research.predictive.preprocessing import (
    PreprocessingSpec,
    PreprocessingStep,
    canonicalize_preprocessing_json,
    default_preprocessing_spec,
    require_train_only_fit_roles,
)
from trading_framework.research.predictive.spec import (
    PredictiveStudySpec,
    compute_definition_hash,
    load_predictive_study_spec,
    load_predictive_study_spec_from_dict,
)
from trading_framework.research.predictive.splitting import (
    FoldRole,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    assign_purged_walk_forward_folds,
)

__all__ = [
    "EstimatorDescription",
    "EstimatorSpec",
    "FeatureMatrixSpec",
    "FeatureSpec",
    "FeatureTransform",
    "FittedPredictiveEstimator",
    "FoldRole",
    "LabelKind",
    "LabelSpec",
    "LabelledFeatureMatrix",
    "MatrixExclusionCounts",
    "PredictiveEstimator",
    "PredictiveExtraError",
    "PredictiveMatrixError",
    "PredictiveSpecError",
    "PredictiveStudySpec",
    "PreprocessingSpec",
    "PreprocessingStep",
    "PurgedWalkForwardSplitMode",
    "PurgedWalkForwardSplitSpec",
    "TaskType",
    "assign_purged_walk_forward_folds",
    "build_labelled_feature_matrix",
    "canonicalize_preprocessing_json",
    "compute_definition_hash",
    "default_preprocessing_spec",
    "load_predictive_study_spec",
    "load_predictive_study_spec_from_dict",
    "require_train_only_fit_roles",
]
