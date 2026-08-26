"""Tests for Predictive Research dataset fingerprinting (D-S039-11)."""

from __future__ import annotations

from datetime import UTC, datetime

from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis.identity.component import (
    ComponentId,
    ComponentVersion,
    ImplementationId,
    ImplementationVersion,
)
from trading_framework.market_analysis.identity.computation import ComputationIdentity
from trading_framework.market_analysis.models.output_ref import OutputRef
from trading_framework.market_analysis.models.outputs import OutputId
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.datasets.predictive import (
    DATASET_ID_HEX_LENGTH,
    compute_dataset_fingerprint,
    derive_dataset_id,
)
from trading_framework.research.predictive import (
    FeatureMatrixSpec,
    FeatureSpec,
    LabelKind,
    LabelSpec,
    PredictiveStudySpec,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    compute_definition_hash,
)
from trading_framework.time.models.timeframe import Timeframe


def _dataset_ref(*, source_id: str = "test") -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier("ES.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id=source_id,
        ),
        version=1,
    )


def _time_range(*, end_day: int = 2) -> TimeRange:
    return TimeRange(
        start=datetime(2024, 1, 1, tzinfo=UTC),
        end=datetime(2024, 1, end_day, tzinfo=UTC),
    )


def _study(
    *,
    alias: str = "atr_14",
    fold_count: int = 2,
    dataset_ref: DatasetRef | None = None,
    time_range: TimeRange | None = None,
    label: LabelSpec | None = None,
) -> PredictiveStudySpec:
    return PredictiveStudySpec(
        study_id="atr_forward_return",
        dataset_ref=dataset_ref or _dataset_ref(),
        time_range=time_range or _time_range(),
        features=FeatureMatrixSpec(
            features=(
                FeatureSpec(
                    component_id=ComponentId("volatility.atr"),
                    parameters=CanonicalParameters.from_mapping({"period": 14}),
                    output_id=OutputId("value"),
                    alias=alias,
                ),
            )
        ),
        label=label or LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("5m")),
        split=PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.EXPANDING,
            fold_count=fold_count,
            test_span=Timeframe("30m"),
            embargo_span=Timeframe("5m"),
            min_train_rows=5,
        ),
    )


def _output_ref(*, implementation_version: str = "1.0.0") -> OutputRef:
    identity = ComputationIdentity(
        component_id=ComponentId("volatility.atr"),
        component_version=ComponentVersion("1.0.0"),
        implementation_id=ImplementationId("numpy.atr"),
        implementation_version=ImplementationVersion(implementation_version),
        parameters=CanonicalParameters.from_mapping({"period": 14}),
        dataset_ref=_dataset_ref(),
        computation_timeframe=Timeframe("1m"),
        requested_range=_time_range(),
        dependency_keys=(),
    )
    return OutputRef(computation_identity=identity, output_id=OutputId("value"))


def test_fingerprint_is_stable_for_unchanged_inputs() -> None:
    spec = _study()
    lineage = {"atr_14": _output_ref()}
    first = compute_dataset_fingerprint(
        definition_hash=spec.definition_hash or compute_definition_hash(spec),
        feature_lineage=lineage,
        dataset_ref=spec.dataset_ref,
        time_range=spec.time_range,
    )
    second = compute_dataset_fingerprint(
        definition_hash=spec.definition_hash or compute_definition_hash(spec),
        feature_lineage=lineage,
        dataset_ref=spec.dataset_ref,
        time_range=spec.time_range,
    )

    assert first == second
    assert len(first) == 64
    assert derive_dataset_id(first) == first[:DATASET_ID_HEX_LENGTH]
    assert len(derive_dataset_id(first)) == DATASET_ID_HEX_LENGTH


def test_fingerprint_changes_when_a_spec_field_changes() -> None:
    lineage = {"atr_14": _output_ref()}
    baseline = compute_dataset_fingerprint(
        definition_hash=_study().definition_hash or "",
        feature_lineage=lineage,
        dataset_ref=_study().dataset_ref,
        time_range=_study().time_range,
    )
    renamed = compute_dataset_fingerprint(
        definition_hash=_study(alias="atr_21").definition_hash or "",
        feature_lineage={"atr_21": _output_ref()},
        dataset_ref=_study().dataset_ref,
        time_range=_study().time_range,
    )
    relabelled = compute_dataset_fingerprint(
        definition_hash=_study(
            label=LabelSpec(kind=LabelKind.BINARY, horizon=Timeframe("5m"), threshold=0.0)
        ).definition_hash
        or "",
        feature_lineage=lineage,
        dataset_ref=_study().dataset_ref,
        time_range=_study().time_range,
    )
    resplit = compute_dataset_fingerprint(
        definition_hash=_study(fold_count=3).definition_hash or "",
        feature_lineage=lineage,
        dataset_ref=_study().dataset_ref,
        time_range=_study().time_range,
    )

    assert renamed != baseline
    assert relabelled != baseline
    assert resplit != baseline


def test_fingerprint_changes_when_lineage_dataset_or_range_changes() -> None:
    spec = _study()
    definition_hash = spec.definition_hash or compute_definition_hash(spec)
    baseline = compute_dataset_fingerprint(
        definition_hash=definition_hash,
        feature_lineage={"atr_14": _output_ref()},
        dataset_ref=spec.dataset_ref,
        time_range=spec.time_range,
    )
    lineage_changed = compute_dataset_fingerprint(
        definition_hash=definition_hash,
        feature_lineage={"atr_14": _output_ref(implementation_version="1.0.1")},
        dataset_ref=spec.dataset_ref,
        time_range=spec.time_range,
    )
    dataset_changed = compute_dataset_fingerprint(
        definition_hash=definition_hash,
        feature_lineage={"atr_14": _output_ref()},
        dataset_ref=_dataset_ref(source_id="other"),
        time_range=spec.time_range,
    )
    range_changed = compute_dataset_fingerprint(
        definition_hash=definition_hash,
        feature_lineage={"atr_14": _output_ref()},
        dataset_ref=spec.dataset_ref,
        time_range=_time_range(end_day=3),
    )

    assert lineage_changed != baseline
    assert dataset_changed != baseline
    assert range_changed != baseline
