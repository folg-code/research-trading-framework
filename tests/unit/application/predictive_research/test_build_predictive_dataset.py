"""Tests for the Predictive Research dataset application workflow."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from trading_framework.application.predictive_research import (
    BuildPredictiveDatasetRequest,
    build_predictive_dataset,
)
from trading_framework.core.types import Price, Volume
from trading_framework.market.datasets import DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.outputs import OutputId
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.datasets.predictive import PredictiveDatasetRepository
from trading_framework.research.predictive import (
    FeatureMatrixSpec,
    FeatureSpec,
    FoldRole,
    LabelKind,
    LabelSpec,
    PredictiveStudySpec,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
)
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

_BAR_COUNT = 180
_ATR_PERIOD = 2


def _dataset_ref() -> DatasetRef:
    return DatasetRef.parse("ES.c.0|ohlcv|1m|csv|predictive-fixture@1")


def _timestamps() -> tuple[datetime, ...]:
    start = datetime(2024, 1, 2, 14, 0, tzinfo=UTC)
    return tuple(start + timedelta(minutes=index) for index in range(_BAR_COUNT))


def _synthetic_bars() -> tuple[MarketBar, ...]:
    bars: list[MarketBar] = []
    for index, observed_at in enumerate(_timestamps()):
        close = 100.0 + (index * 0.05)
        bars.append(
            MarketBar(
                open=Price(Decimal(str(round(close, 4)))),
                high=Price(Decimal(str(round(close + 0.4, 4)))),
                low=Price(Decimal(str(round(close - 0.4, 4)))),
                close=Price(Decimal(str(round(close, 4)))),
                volume=Volume(1_000),
                observed_at=observed_at,
                available_at=observed_at + timedelta(minutes=1),
            )
        )
    return tuple(bars)


def _study(*, fold_count: int = 2) -> PredictiveStudySpec:
    timestamps = _timestamps()
    return PredictiveStudySpec(
        study_id="atr_forward_return",
        dataset_ref=_dataset_ref(),
        time_range=TimeRange(start=timestamps[0], end=timestamps[-1]),
        features=FeatureMatrixSpec(
            features=(
                FeatureSpec(
                    component_id=ComponentId("volatility.atr"),
                    parameters=CanonicalParameters.from_mapping({"period": _ATR_PERIOD}),
                    output_id=OutputId("value"),
                    alias="atr",
                ),
            )
        ),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("5m")),
        split=PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.EXPANDING,
            fold_count=fold_count,
            test_span=Timeframe("30m"),
            embargo_span=Timeframe("5m"),
            min_train_rows=5,
        ),
    )


def test_build_predictive_dataset_persists_envelope_with_fold_roles(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    spec = _study()
    clock = FixedClock(datetime(2024, 6, 1, 12, 0, tzinfo=UTC))

    result = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=spec,
            storage_root=storage_root,
            persist=True,
            preloaded_bars=_synthetic_bars(),
            clock=clock,
        )
    )
    loaded = PredictiveDatasetRepository(storage_root).read(result.dataset_ref)

    assert result.persisted is True
    assert result.dataset_id == result.fingerprint[:16]
    assert result.envelope.manifest.created_at_utc == clock.now()
    assert "fold_id" in result.envelope.features.columns
    assert "fold_role" in result.envelope.features.columns
    roles = set(result.envelope.features.get_column("fold_role").to_list())
    assert FoldRole.TRAIN.value in roles
    assert FoldRole.TEST.value in roles
    assert loaded.manifest.dataset_fingerprint == result.fingerprint
    assert (
        loaded.features.get_column("fold_role").to_list()
        == result.envelope.features.get_column("fold_role").to_list()
    )
    assert (
        loaded.features.get_column("label").to_list()
        == result.envelope.features.get_column("label").to_list()
    )
    assert "atr" in loaded.features.columns


def test_rebuild_from_same_spec_yields_identical_fingerprint(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    spec = _study()
    bars = _synthetic_bars()
    first = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=spec,
            storage_root=storage_root,
            persist=False,
            preloaded_bars=bars,
            clock=FixedClock(datetime(2024, 6, 1, 12, 0, tzinfo=UTC)),
        )
    )
    second = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=spec,
            storage_root=storage_root,
            persist=False,
            preloaded_bars=bars,
            clock=FixedClock(datetime(2024, 6, 2, 12, 0, tzinfo=UTC)),
        )
    )

    assert first.fingerprint == second.fingerprint
    assert first.dataset_id == second.dataset_id
    assert first.envelope.manifest.created_at_utc != second.envelope.manifest.created_at_utc


def test_spec_field_change_yields_different_fingerprint(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    bars = _synthetic_bars()
    baseline = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=_study(fold_count=2),
            storage_root=storage_root,
            persist=False,
            preloaded_bars=bars,
        )
    )
    changed = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=_study(fold_count=1),
            storage_root=storage_root,
            persist=False,
            preloaded_bars=bars,
        )
    )

    assert changed.fingerprint != baseline.fingerprint
    assert changed.dataset_id != baseline.dataset_id
