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
    FeatureTransform,
    IncompatibleSampleTaskError,
    LabelKind,
    LabelSpec,
    PredictiveSpecError,
    PredictiveStudySpec,
    PredictiveTask,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    ReservedPredictiveTaskError,
    ReservedSampleKindError,
    SampleDirection,
    SampleKind,
    SampleSpec,
    compute_definition_hash,
    load_predictive_study_spec,
    load_predictive_study_spec_from_dict,
)
from trading_framework.time.models.timeframe import Timeframe

# Recorded on `main` @ a004e8d, before S056-T002 introduced `sample`/`task`
# (SPRINT_056.md acceptance criterion 1: asserted against a recorded value,
# never recomputed on both sides). This is `compute_definition_hash(_study())`
# as it existed prior to this change.
_PRE_SPRINT_056_DEFINITION_HASH = "105b0ca2d31aa1c6a1d6b2c79f4093dd1f8119ac22aa3e341f259eb437f5a903"

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
    transformed = compute_definition_hash(
        PredictiveStudySpec(
            study_id="atr_forward_return",
            dataset_ref=_dataset_ref(),
            time_range=_time_range(),
            features=FeatureMatrixSpec(
                features=(
                    FeatureSpec(
                        component_id=ComponentId("volatility.atr"),
                        parameters=CanonicalParameters.from_mapping({"period": 14}),
                        output_id=OutputId("atr"),
                        alias="atr_14",
                        transform=FeatureTransform.LOG,
                    ),
                )
            ),
            label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("15m")),
            split=_split(),
        )
    )
    shifted_range = compute_definition_hash(
        PredictiveStudySpec(
            study_id="atr_forward_return",
            dataset_ref=_dataset_ref(),
            time_range=TimeRange(
                start=datetime(2025, 1, 2, tzinfo=UTC),
                end=datetime(2025, 6, 30, 23, 59, 59, tzinfo=UTC),
            ),
            features=FeatureMatrixSpec(features=(_feature(),)),
            label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("15m")),
            split=_split(),
        )
    )
    coarser_evaluation = compute_definition_hash(
        PredictiveStudySpec(
            study_id="atr_forward_return",
            dataset_ref=_dataset_ref(),
            time_range=_time_range(),
            features=FeatureMatrixSpec(features=(_feature(),)),
            label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("15m")),
            split=_split(),
            evaluation_timeframe=Timeframe("5m"),
        )
    )

    hashes = {
        baseline,
        renamed,
        relabelled,
        resplit,
        transformed,
        shifted_range,
        coarser_evaluation,
    }
    assert len(hashes) == 7


def test_definition_hash_changes_when_feature_order_changes() -> None:
    atr_14 = _feature(alias="atr_14")
    atr_21 = _feature(alias="atr_21")
    first = PredictiveStudySpec(
        study_id="atr_forward_return",
        dataset_ref=_dataset_ref(),
        time_range=_time_range(),
        features=FeatureMatrixSpec(features=(atr_14, atr_21)),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("15m")),
        split=_split(),
    )
    swapped = PredictiveStudySpec(
        study_id="atr_forward_return",
        dataset_ref=_dataset_ref(),
        time_range=_time_range(),
        features=FeatureMatrixSpec(features=(atr_21, atr_14)),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("15m")),
        split=_split(),
    )

    assert compute_definition_hash(first) != compute_definition_hash(swapped)


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


def test_yaml_load_matches_programmatic_definition_hash(tmp_path: Path) -> None:
    path = tmp_path / "study.yaml"
    path.write_text(_YAML_STUDY, encoding="utf-8")

    loaded = load_predictive_study_spec(path)

    assert loaded.definition_hash == _study().definition_hash


def test_yml_extension_loads_like_yaml(tmp_path: Path) -> None:
    path = tmp_path / "study.yml"
    path.write_text(_YAML_STUDY, encoding="utf-8")

    loaded = load_predictive_study_spec(path)

    assert loaded.study_id == "atr_forward_return"
    assert loaded.definition_hash == _study().definition_hash


def test_loader_ignores_stale_definition_hash_in_payload() -> None:
    payload = _study().to_dict()
    payload["definition_hash"] = "0" * 64

    loaded = load_predictive_study_spec_from_dict(payload)

    assert loaded.definition_hash != "0" * 64
    assert loaded.definition_hash == compute_definition_hash(loaded)
    assert loaded.definition_hash == _study().definition_hash


def test_dataset_ref_string_form_round_trips_to_the_same_hash() -> None:
    payload = _study().to_dict()
    payload["dataset_ref"] = "ES.c.0|ohlcv|1m|csv|test@1"
    payload.pop("definition_hash", None)

    loaded = load_predictive_study_spec_from_dict(payload)

    assert loaded.dataset_ref == _dataset_ref()
    assert loaded.definition_hash == _study().definition_hash


def test_empty_study_id_is_rejected() -> None:
    with pytest.raises(PredictiveSpecError, match="study_id must be non-empty"):
        PredictiveStudySpec(
            study_id="   ",
            dataset_ref=_dataset_ref(),
            time_range=_time_range(),
            features=FeatureMatrixSpec(features=(_feature(),)),
            label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("15m")),
            split=_split(),
        )


def test_evaluation_timeframe_rejects_tick() -> None:
    with pytest.raises(PredictiveSpecError, match="evaluation_timeframe must be a bar duration"):
        PredictiveStudySpec(
            study_id="tick_eval",
            dataset_ref=_dataset_ref(),
            time_range=_time_range(),
            features=FeatureMatrixSpec(features=(_feature(),)),
            label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("15m")),
            split=_split(),
            evaluation_timeframe=Timeframe("tick"),
        )


def test_missing_study_field_is_rejected() -> None:
    payload = _study().to_dict()
    del payload["features"]

    with pytest.raises(PredictiveSpecError, match="missing field: features"):
        PredictiveStudySpec.from_dict(payload)


def test_invalid_json_study_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "study.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(PredictiveSpecError, match="invalid JSON study file"):
        load_predictive_study_spec(path)


def test_yaml_study_must_be_a_mapping(tmp_path: Path) -> None:
    path = tmp_path / "study.yaml"
    path.write_text("- not_a_mapping\n", encoding="utf-8")

    with pytest.raises(PredictiveSpecError, match="must deserialize to a mapping"):
        load_predictive_study_spec(path)


# --- S056-T002: SampleSpec / PredictiveTask wiring, default elision, refusals ---


def test_definition_hash_is_byte_identical_to_the_recorded_pre_sprint_value() -> None:
    """Acceptance criterion 1 (SPRINT_056.md): asserted against a value recorded
    before this sprint's change, not recomputed with the new code on both sides.
    """
    assert _study().definition_hash == _PRE_SPRINT_056_DEFINITION_HASH


def test_default_sample_and_task_are_omitted_from_to_dict() -> None:
    payload = _study().to_dict()

    assert "sample" not in payload
    assert "task" not in payload


def test_explicit_every_bar_forward_return_hashes_identically_to_omitted() -> None:
    omitted = _study()
    explicit = PredictiveStudySpec(
        study_id="atr_forward_return",
        dataset_ref=_dataset_ref(),
        time_range=_time_range(),
        features=FeatureMatrixSpec(features=(_feature(),)),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("15m")),
        split=_split(),
        sample=SampleSpec(kind=SampleKind.EVERY_BAR),
        task=PredictiveTask.FORWARD_RETURN,
    )

    assert explicit.definition_hash == omitted.definition_hash
    assert explicit.to_dict() == omitted.to_dict()


def test_signal_occurrences_sample_is_present_in_to_dict() -> None:
    spec = PredictiveStudySpec(
        study_id="signal_quality_study",
        dataset_ref=_dataset_ref(),
        time_range=_time_range(),
        features=FeatureMatrixSpec(features=(_feature(),)),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("15m")),
        split=_split(),
        sample=SampleSpec(
            kind=SampleKind.SIGNAL_OCCURRENCES,
            signal_model_file="models/breakout.yaml",
            signal_model_id="breakout_v1",
        ),
        task=PredictiveTask.SIGNAL_QUALITY,
    )
    payload = spec.to_dict()

    assert payload["sample"] == {
        "kind": "signal_occurrences",
        "signal_model_file": "models/breakout.yaml",
        "signal_model_id": "breakout_v1",
    }
    assert payload["task"] == "SIGNAL_QUALITY"
    assert spec.definition_hash != _study().definition_hash


def test_sample_and_task_round_trip_through_dict() -> None:
    original = PredictiveStudySpec(
        study_id="signal_quality_study",
        dataset_ref=_dataset_ref(),
        time_range=_time_range(),
        features=FeatureMatrixSpec(features=(_feature(),)),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("15m")),
        split=_split(),
        sample=SampleSpec(
            kind=SampleKind.SIGNAL_OCCURRENCES,
            signal_model_file="models/breakout.yaml",
            signal_model_id="breakout_v1",
            direction=SampleDirection.SHORT,
        ),
        task=PredictiveTask.SIGNAL_QUALITY,
    )

    restored = PredictiveStudySpec.from_dict(original.to_dict())

    assert restored.sample == original.sample
    assert restored.task is original.task
    assert restored.definition_hash == original.definition_hash


def test_every_bar_signal_quality_is_refused_when_wiring_the_study_spec() -> None:
    with pytest.raises(IncompatibleSampleTaskError, match="not compatible"):
        PredictiveStudySpec(
            study_id="incoherent_study",
            dataset_ref=_dataset_ref(),
            time_range=_time_range(),
            features=FeatureMatrixSpec(features=(_feature(),)),
            label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("15m")),
            split=_split(),
            task=PredictiveTask.SIGNAL_QUALITY,
        )


@pytest.mark.parametrize(
    ("sample_kind", "owner"),
    [
        ("strategy_trades", "16F"),
        ("labelled_setups", "16F"),
        ("sessions_or_windows", "later, unassigned"),
    ],
)
def test_reserved_sample_kind_is_refused_when_loading_a_study(sample_kind: str, owner: str) -> None:
    payload = _study().to_dict()
    payload["sample"] = {"kind": sample_kind}

    with pytest.raises(ReservedSampleKindError, match=owner):
        PredictiveStudySpec.from_dict(payload)


@pytest.mark.parametrize(
    ("task_name", "owner"),
    [
        ("TRADE_OUTCOME", "16F"),
        ("NO_TRADE_FILTER", "16F"),
        ("REGIME_CLASSIFICATION", "later, unassigned"),
        ("VOLATILITY_FORECAST", "later, unassigned"),
        ("DISCRETIONARY_SETUP_CLASSIFICATION", "later, unassigned"),
    ],
)
def test_reserved_predictive_task_is_refused_when_loading_a_study(
    task_name: str, owner: str
) -> None:
    payload = _study().to_dict()
    payload["task"] = task_name

    with pytest.raises(ReservedPredictiveTaskError, match=owner):
        PredictiveStudySpec.from_dict(payload)


def test_sample_payload_must_be_a_mapping() -> None:
    payload = _study().to_dict()
    payload["sample"] = "every_bar"

    with pytest.raises(PredictiveSpecError, match="sample must be a mapping"):
        PredictiveStudySpec.from_dict(payload)
