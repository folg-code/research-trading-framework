"""Unit tests for PredictiveStudySpec hash, round-trip, and loading."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.outputs import OutputId
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.predictive import (
    FeatureMatrixSpec,
    FeatureSpec,
    LabelKind,
    LabelSpec,
    PredictiveSpecError,
    PredictiveStudySpec,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    compute_definition_hash,
    load_predictive_study_spec,
)
from trading_framework.time.models.timeframe import Timeframe

_YAML_STUDY = """
study:
  study_id: atr_forward_return
  dataset_ref:
    dataset_id: ES.c.0|ohlcv|1m|csv|test
    version: 1
  time_range:
    start: 2025-01-01
    end: 2025-06-30
  evaluation_timeframe: 1m
  features:
    - component_id: volatility.atr
      parameters:
        period: 14
      output_id: atr
      alias: atr_14
      transform: NONE
  label:
    kind: REGRESSION
    horizon: 15m
  split:
    mode: EXPANDING
    fold_count: 4
    test_span: 20d
    embargo_span: 15m
    min_train_rows: 500
"""


def _dataset_ref() -> DatasetRef:
    return DatasetRef.parse("ES.c.0|ohlcv|1m|csv|test@1")


def _time_range() -> TimeRange:
    return TimeRange(
        start=datetime(2025, 1, 1, tzinfo=UTC),
        end=datetime(2025, 6, 30, 23, 59, 59, tzinfo=UTC),
    )


def _feature(*, alias: str = "atr_14") -> FeatureSpec:
    return FeatureSpec(
        component_id=ComponentId("volatility.atr"),
        parameters=CanonicalParameters.from_mapping({"period": 14}),
        output_id=OutputId("atr"),
        alias=alias,
    )


def _split(*, fold_count: int = 4) -> PurgedWalkForwardSplitSpec:
    return PurgedWalkForwardSplitSpec(
        mode=PurgedWalkForwardSplitMode.EXPANDING,
        fold_count=fold_count,
        test_span=Timeframe("20d"),
        embargo_span=Timeframe("15m"),
        min_train_rows=500,
    )


def _study(
    *,
    alias: str = "atr_14",
    label: LabelSpec | None = None,
    fold_count: int = 4,
) -> PredictiveStudySpec:
    return PredictiveStudySpec(
        study_id="atr_forward_return",
        dataset_ref=_dataset_ref(),
        time_range=_time_range(),
        features=FeatureMatrixSpec(features=(_feature(alias=alias),)),
        label=label or LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("15m")),
        split=_split(fold_count=fold_count),
    )


def test_study_spec_computes_horizon_bars() -> None:
    spec = _study()

    assert spec.label_horizon_bars() == 15
    assert spec.definition_hash is not None
    assert len(spec.definition_hash) == 64


def test_definition_hash_is_stable_for_identical_spec() -> None:
    first = compute_definition_hash(_study())
    second = compute_definition_hash(_study())

    assert first == second
    assert first == _study().definition_hash


def test_definition_hash_changes_when_a_field_changes() -> None:
    baseline = compute_definition_hash(_study())

    renamed = compute_definition_hash(_study(alias="atr_21"))
    relabelled = compute_definition_hash(
        _study(
            label=LabelSpec(
                kind=LabelKind.BINARY,
                horizon=Timeframe("15m"),
                threshold=0.0,
            )
        )
    )
    resplit = compute_definition_hash(_study(fold_count=5))

    assert renamed != baseline
    assert relabelled != baseline
    assert resplit != baseline
    assert len({baseline, renamed, relabelled, resplit}) == 4


def test_dict_round_trip_preserves_hash() -> None:
    original = _study()

    restored = PredictiveStudySpec.from_dict(original.to_dict())

    assert restored.study_id == original.study_id
    assert restored.label.kind is LabelKind.REGRESSION
    assert restored.split.fold_count == 4
    assert restored.definition_hash == original.definition_hash
    assert restored.to_dict() == original.to_dict()


def test_yaml_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "study.yaml"
    path.write_text(_YAML_STUDY, encoding="utf-8")

    loaded = load_predictive_study_spec(path)
    restored = PredictiveStudySpec.from_dict(loaded.to_dict())

    assert loaded.study_id == "atr_forward_return"
    assert loaded.features.features[0].alias == "atr_14"
    assert loaded.label.kind is LabelKind.REGRESSION
    assert loaded.label_horizon_bars() == 15
    assert restored.definition_hash == loaded.definition_hash
    assert restored.to_dict() == loaded.to_dict()


def test_json_round_trip(tmp_path: Path) -> None:
    original = _study()
    path = tmp_path / "study.json"
    path.write_text(json.dumps(original.to_dict()), encoding="utf-8")

    loaded = load_predictive_study_spec(path)

    assert loaded.definition_hash == original.definition_hash
    assert loaded.to_dict() == original.to_dict()


def test_horizon_must_align_to_evaluation_timeframe() -> None:
    with pytest.raises(PredictiveSpecError, match="not an integer multiple"):
        PredictiveStudySpec(
            study_id="misaligned",
            dataset_ref=_dataset_ref(),
            time_range=_time_range(),
            features=FeatureMatrixSpec(features=(_feature(),)),
            label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("15m")),
            split=_split(),
            evaluation_timeframe=Timeframe("1h"),
        )


def test_missing_study_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(PredictiveSpecError, match="study file not found"):
        load_predictive_study_spec(tmp_path / "missing.yaml")


def test_unsupported_extension_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "study.toml"
    path.write_text("study_id = 'x'", encoding="utf-8")

    with pytest.raises(PredictiveSpecError, match="unsupported study file extension"):
        load_predictive_study_spec(path)
