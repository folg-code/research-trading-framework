"""Unit tests for FeatureSpec and FeatureMatrixSpec."""

from __future__ import annotations

import pytest

from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.outputs import OutputId
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.research.predictive import (
    FeatureMatrixSpec,
    FeatureSpec,
    FeatureTransform,
    PredictiveSpecError,
)


def _atr_feature(*, alias: str = "atr_14") -> FeatureSpec:
    return FeatureSpec(
        component_id=ComponentId("volatility.atr"),
        parameters=CanonicalParameters.from_mapping({"period": 14}),
        output_id=OutputId("atr"),
        alias=alias,
    )


def test_feature_spec_defaults_transform_to_none() -> None:
    feature = _atr_feature()

    assert feature.transform is FeatureTransform.NONE
    assert feature.alias == "atr_14"


def test_feature_spec_strips_alias() -> None:
    feature = FeatureSpec(
        component_id=ComponentId("volatility.atr"),
        parameters=CanonicalParameters.from_mapping({"period": 14}),
        output_id=OutputId("atr"),
        alias="  atr_14  ",
        transform=FeatureTransform.LOG,
    )

    assert feature.alias == "atr_14"
    assert feature.transform is FeatureTransform.LOG


def test_empty_feature_alias_is_rejected() -> None:
    with pytest.raises(PredictiveSpecError, match="feature alias must be non-empty"):
        FeatureSpec(
            component_id=ComponentId("volatility.atr"),
            parameters=CanonicalParameters.from_mapping({"period": 14}),
            output_id=OutputId("atr"),
            alias="   ",
        )


def test_feature_matrix_rejects_empty_features() -> None:
    with pytest.raises(PredictiveSpecError, match="at least one feature"):
        FeatureMatrixSpec(features=())


def test_duplicate_feature_aliases_are_rejected() -> None:
    with pytest.raises(PredictiveSpecError, match="feature aliases must be unique"):
        FeatureMatrixSpec(features=(_atr_feature(), _atr_feature()))


def test_feature_matrix_accepts_unique_aliases() -> None:
    matrix = FeatureMatrixSpec(
        features=(
            _atr_feature(alias="atr_14"),
            _atr_feature(alias="atr_21"),
        )
    )

    assert [feature.alias for feature in matrix.features] == ["atr_14", "atr_21"]


def test_feature_spec_dict_round_trip() -> None:
    original = FeatureSpec(
        component_id=ComponentId("trend.ema"),
        parameters=CanonicalParameters.from_mapping({"period": 20}),
        output_id=OutputId("ema"),
        alias="ema_20",
        transform=FeatureTransform.DIFF,
    )

    restored = FeatureSpec.from_dict(original.to_dict())

    assert restored.component_id.value == "trend.ema"
    assert restored.parameters.to_json_dict() == {"period": 20}
    assert restored.output_id.value == "ema"
    assert restored.alias == "ema_20"
    assert restored.transform is FeatureTransform.DIFF


def test_invalid_feature_transform_is_rejected() -> None:
    payload = _atr_feature().to_dict()
    payload["transform"] = "SCALE"

    with pytest.raises(PredictiveSpecError, match="invalid feature transform"):
        FeatureSpec.from_dict(payload)


def test_feature_transform_is_the_declared_bounded_set() -> None:
    assert {member.value for member in FeatureTransform} == {
        "NONE",
        "LOG",
        "DIFF",
        "PCT_CHANGE",
        "RANK",
    }


def test_feature_spec_from_dict_rejects_missing_field() -> None:
    payload = _atr_feature().to_dict()
    del payload["component_id"]

    with pytest.raises(PredictiveSpecError, match="missing field: component_id"):
        FeatureSpec.from_dict(payload)


def test_feature_spec_from_dict_rejects_non_mapping_parameters() -> None:
    payload = _atr_feature().to_dict()
    payload["parameters"] = [14]

    with pytest.raises(PredictiveSpecError, match="parameters must be a mapping"):
        FeatureSpec.from_dict(payload)


def test_feature_matrix_from_dict_rejects_non_sequence() -> None:
    with pytest.raises(PredictiveSpecError, match="must be a sequence"):
        FeatureMatrixSpec.from_dict({"alias": "atr_14"})


def test_feature_matrix_from_dict_rejects_non_mapping_items() -> None:
    with pytest.raises(PredictiveSpecError, match="each feature must be a mapping"):
        FeatureMatrixSpec.from_dict(["atr_14"])


def test_feature_matrix_from_dict_rejects_empty_list() -> None:
    with pytest.raises(PredictiveSpecError, match="at least one feature"):
        FeatureMatrixSpec.from_dict([])


def test_feature_matrix_from_dict_rejects_aliases_that_collide_after_strip() -> None:
    first = _atr_feature(alias="atr_14").to_dict()
    second = _atr_feature(alias="atr_14").to_dict()
    second["alias"] = "  atr_14  "

    with pytest.raises(PredictiveSpecError, match="feature aliases must be unique"):
        FeatureMatrixSpec.from_dict([first, second])
