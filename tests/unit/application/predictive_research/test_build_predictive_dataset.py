"""Tests for the Predictive Research dataset application workflow."""

from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from trading_framework.application.predictive_research import (
    BuildPredictiveDatasetRequest,
    build_predictive_dataset,
)
from trading_framework.application.predictive_research.build_predictive_dataset import (
    PredictiveDatasetError,
)
from trading_framework.core.types import Price, Volume
from trading_framework.market.datasets import DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.outputs import OutputId
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.datasets.predictive import (
    PREDICTIVE_DATASET_SCHEMA_V2,
    PredictiveDatasetRepository,
)
from trading_framework.research.predictive import (
    FeatureMatrixSpec,
    FeatureSpec,
    FoldRole,
    LabelKind,
    LabelSpec,
    PredictiveStudySpec,
    PredictiveTask,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    SampleKind,
    SampleSpec,
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


def _synthetic_bars(*, close_start: float = 100.0) -> tuple[MarketBar, ...]:
    bars: list[MarketBar] = []
    for index, observed_at in enumerate(_timestamps()):
        close = close_start + (index * 0.05)
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


def _study(*, fold_count: int = 2, sample: SampleSpec | None = None) -> PredictiveStudySpec:
    timestamps = _timestamps()
    resolved_sample = sample if sample is not None else SampleSpec(kind=SampleKind.EVERY_BAR)
    task = PredictiveTask.SIGNAL_QUALITY if sample is not None else PredictiveTask.FORWARD_RETURN
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
        sample=resolved_sample,
        task=task,
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
    assert "forward_return" in loaded.features.columns
    assert result.envelope.manifest.exclusion_counts["labelled_rows"] > 0
    assert "incomplete_horizon" in result.envelope.manifest.exclusion_counts
    assert result.envelope.manifest.fold_summary["fold_count"] == 2
    role_counts = result.envelope.manifest.fold_summary["role_counts"]
    assert role_counts[FoldRole.TRAIN.value] > 0
    assert role_counts[FoldRole.TEST.value] > 0
    assert role_counts[FoldRole.PURGED.value] > 0
    assert role_counts[FoldRole.EMBARGOED.value] > 0
    assert loaded.manifest.schema_version == PREDICTIVE_DATASET_SCHEMA_V2
    provenance = result.envelope.manifest.sample_provenance
    assert provenance is not None
    assert provenance.kind is SampleKind.EVERY_BAR
    assert provenance.task is PredictiveTask.FORWARD_RETURN
    # "The whole grid was used" is a read (equal counts, no drops), not an
    # inference from a missing key (Finding 5, SPRINT_056.md).
    assert provenance.universe_row_count == provenance.resolved_row_count
    assert (
        provenance.universe_row_count == result.envelope.manifest.exclusion_counts["candidate_rows"]
    )
    assert provenance.drop_counts == {}
    assert loaded.manifest.sample_provenance == provenance


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


def test_rebuild_with_different_bar_values_keeps_fingerprint(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    spec = _study()
    first = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=spec,
            storage_root=storage_root,
            persist=False,
            preloaded_bars=_synthetic_bars(close_start=100.0),
        )
    )
    second = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=spec,
            storage_root=storage_root,
            persist=False,
            preloaded_bars=_synthetic_bars(close_start=250.0),
        )
    )

    assert first.fingerprint == second.fingerprint
    assert first.dataset_id == second.dataset_id
    assert (
        first.envelope.features.get_column("label").to_list()
        != second.envelope.features.get_column("label").to_list()
    )


def test_application_workflow_uses_run_analysis_and_existing_builders() -> None:
    source = Path(build_predictive_dataset.__code__.co_filename).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)

    assert "trading_framework.application.market_analysis.run_analysis" in imported
    assert "trading_framework.research.predictive.matrix" in imported
    assert "trading_framework.research.predictive.splitting" in imported
    assert "run_analysis" in source
    assert "build_labelled_feature_matrix" in source
    assert "assign_purged_walk_forward_folds" in source
    assert not any(
        name == root or name.startswith(f"{root}.")
        for name in imported
        for root in ("sklearn", "xgboost", "lightgbm", "catboost", "torch")
    )


def test_signal_occurrences_sample_is_refused_before_resolution_exists(tmp_path: Path) -> None:
    """S056-T003: refuse rather than silently build every_bar under a mislabelled manifest.

    ``signal_occurrences`` resolution (evaluate_models -> materialize_signal_
    occurrences -> filter-late row selection) is S056-T004, not yet
    implemented. Building the whole grid anyway while the manifest claimed a
    resolved sample would be exactly the silent-inference failure Finding 5
    warns against.
    """
    storage_root = tmp_path / "workspace"
    spec = _study(
        sample=SampleSpec(
            kind=SampleKind.SIGNAL_OCCURRENCES,
            signal_model_file="models/breakout.yaml",
            signal_model_id="breakout_v1",
        )
    )

    with pytest.raises(PredictiveDatasetError, match="not yet resolvable"):
        build_predictive_dataset(
            BuildPredictiveDatasetRequest(
                spec=spec,
                storage_root=storage_root,
                persist=False,
                preloaded_bars=_synthetic_bars(),
            )
        )
