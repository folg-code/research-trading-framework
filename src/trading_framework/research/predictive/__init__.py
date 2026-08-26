"""Predictive Research specification contracts — features, labels, study hash."""

from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.features import (
    FeatureMatrixSpec,
    FeatureSpec,
    FeatureTransform,
)
from trading_framework.research.predictive.labels import LabelKind, LabelSpec
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
    "PredictiveSpecError",
    "PredictiveStudySpec",
    "PurgedWalkForwardSplitMode",
    "PurgedWalkForwardSplitSpec",
    "compute_definition_hash",
    "load_predictive_study_spec",
    "load_predictive_study_spec_from_dict",
]
