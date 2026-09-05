"""Tests for the Predictive Research dataset application workflow."""

from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest

from trading_framework.application.market_analysis.run_analysis import (
    RunAnalysisRequest,
    run_analysis,
)
from trading_framework.application.model_evaluation import EvaluateModelsRequest, evaluate_models
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
from trading_framework.market_analysis.assembly.frame import AnalysisFrameRequest
from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.outputs import OutputId
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.model_expression import (
    CompareExpression,
    ComparisonOperator,
    MarketField,
    MarketFieldReference,
)
from trading_framework.research.datasets.predictive import (
    PREDICTIVE_DATASET_SCHEMA_V2,
    PredictiveDatasetRepository,
)
from trading_framework.research.outcomes.calculator import compute_forward_outcomes_for_horizons
from trading_framework.research.outcomes.definition import ForwardOutcomeDefinition
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
    SampleDirection,
    SampleKind,
    SampleSpec,
)
from trading_framework.signal_model.definitions import (
    SignalDirection,
    SignalFiringPolicy,
    SignalModelDefinition,
)
from trading_framework.strategy import (
    OccurrenceMaterializationContext,
    materialize_signal_occurrences,
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


def test_signal_occurrences_sample_requires_signal_model(tmp_path: Path) -> None:
    """S056-T004: refuse rather than silently build every_bar under a mislabelled manifest.

    The declared ``signal_model_file``/``signal_model_id`` name a Signal Model
    by declaration only (ADR-0031 sec1); resolving it into a
    ``SignalModelDefinition`` requires ``request.signal_model`` since no
    file-loading convention exists for Signal Models yet (unlike
    ``PredictiveStudySpec``/``EstimatorSpec``, which have their own loaders).
    """
    storage_root = tmp_path / "workspace"
    spec = _study(
        sample=SampleSpec(
            kind=SampleKind.SIGNAL_OCCURRENCES,
            signal_model_file="models/breakout.yaml",
            signal_model_id="breakout_v1",
        )
    )

    with pytest.raises(PredictiveDatasetError, match=r"requires request\.signal_model"):
        build_predictive_dataset(
            BuildPredictiveDatasetRequest(
                spec=spec,
                storage_root=storage_root,
                persist=False,
                preloaded_bars=_synthetic_bars(),
            )
        )


def _breakout_signal_model(
    *,
    direction: SignalDirection,
    threshold: float = 108.0,
) -> SignalModelDefinition:
    """A dense-then-sparse breakout signal: fires ON_EVENT on every bar with close > threshold.

    Against ``_synthetic_bars()``'s monotonic close ramp this gives a
    multi-bar, mixed-outcome occurrence run (some COMPLETE, some
    INCOMPLETE_HORIZON near the end of the range) with a single component-free
    ``MarketFieldReference`` expression -- no registry/component wiring needed.
    """
    return SignalModelDefinition(
        signal_model_id="breakout_v1",
        expression=CompareExpression(
            operand=MarketFieldReference(field=MarketField.CLOSE),
            operator=ComparisonOperator.GT,
            value=threshold,
        ),
        direction=direction,
        firing_policy=SignalFiringPolicy.ON_EVENT,
    )


def _signal_occurrences_study(*, direction: SignalDirection) -> PredictiveStudySpec:
    """A study over the same fixture as ``_study()``, sized for the sparse occurrence run.

    Threshold 108.0 against ``_synthetic_bars()``'s ramp (close = 100 + idx*0.05)
    fires for idx 161..179 (19 bars); a 5-bar horizon leaves idx 161..174
    (14 rows) COMPLETE and idx 175..179 (5 rows) INCOMPLETE_HORIZON -- both
    exclusion reasons exercised from one fixture. The split spec is sized to
    that ~14-minute kept-row span, not `_study()`'s 30-minute default.
    """
    timestamps = _timestamps()
    return PredictiveStudySpec(
        study_id="breakout_signal_quality",
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
            fold_count=1,
            test_span=Timeframe("3m"),
            embargo_span=Timeframe("1m"),
            min_train_rows=2,
        ),
        sample=SampleSpec(
            kind=SampleKind.SIGNAL_OCCURRENCES,
            signal_model_file="models/breakout.yaml",
            signal_model_id="breakout_v1",
            direction=(
                SampleDirection.SHORT if direction is SignalDirection.SHORT else SampleDirection.ANY
            ),
        ),
        task=PredictiveTask.SIGNAL_QUALITY,
    )


def _occurrences_for(
    *,
    direction: SignalDirection,
    bars: tuple[MarketBar, ...],
) -> pl.DataFrame:
    """Independently derive the canonical occurrence table for cross-checking.

    Reuses ``evaluate_models``/``materialize_signal_occurrences`` exactly as
    ``resolve_signal_occurrences_sample`` does (D-S056-08's mechanism: the
    test must call the SAME functions Signal Research calls, not
    re-implement equivalent logic).
    """
    signal_model = _breakout_signal_model(direction=direction)
    spec = _signal_occurrences_study(direction=direction)
    eval_result = evaluate_models(
        EvaluateModelsRequest(
            dataset_ref=spec.dataset_ref,
            timeframe=spec.dataset_ref.dataset_id.timeframe,
            requested_range=spec.time_range,
            storage_root=Path("unused"),
            signal_models=(signal_model,),
            evaluation_timeframe=spec.evaluation_timeframe,
            preloaded_bars=bars,
        )
    )
    frame = eval_result.analysis.frame
    assert frame is not None
    emissions = eval_result.signal_model_emissions[signal_model.signal_model_id]
    occurrences = materialize_signal_occurrences(
        emissions,
        frame=frame,
        market_view=eval_result.analysis.workspace.market_view,
        context=OccurrenceMaterializationContext(
            signal_model_id=signal_model.signal_model_id,
            instrument=spec.dataset_ref.dataset_id.instrument_id.value,
            evaluation_timeframe=spec.evaluation_timeframe,
            source_dataset_ref=str(spec.dataset_ref),
        ),
    )
    if spec.sample.direction is SampleDirection.SHORT:
        occurrences = occurrences.filter(pl.col("direction") == SignalDirection.SHORT.value)
    return occurrences


def test_signal_occurrences_candidate_rows_equal_occurrence_count(tmp_path: Path) -> None:
    """D-S056-08: candidate_rows == occurrences.height, an equality, and every
    non-labelled occurrence is attributed to exactly one exclusion reason."""
    storage_root = tmp_path / "workspace"
    bars = _synthetic_bars()
    signal_model = _breakout_signal_model(direction=SignalDirection.LONG)
    spec = _signal_occurrences_study(direction=SignalDirection.LONG)
    occurrences = _occurrences_for(direction=SignalDirection.LONG, bars=bars)
    assert occurrences.height == 19

    result = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=spec,
            storage_root=storage_root,
            persist=False,
            preloaded_bars=bars,
            signal_model=signal_model,
        )
    )

    manifest = result.envelope.manifest
    assert manifest.exclusion_counts["candidate_rows"] == occurrences.height
    provenance = manifest.sample_provenance
    assert provenance is not None
    assert provenance.kind is SampleKind.SIGNAL_OCCURRENCES
    assert provenance.universe_row_count == occurrences.height
    accounted = provenance.resolved_row_count + sum(provenance.drop_counts.values())
    assert accounted == occurrences.height
    assert provenance.drop_counts.get("incomplete_horizon", 0) == 5
    assert provenance.resolved_row_count == 14
    assert "null_features" not in provenance.drop_counts

    entity_ids = set(result.envelope.features.get_column("entity_id").unique().to_list())
    assert entity_ids.issubset(set(occurrences.get_column("occurrence_id").to_list()))


def test_signal_occurrences_direction_adjusted_forward_return_matches_signal_research(
    tmp_path: Path,
) -> None:
    """D-S056-06/Finding 4: a SHORT occurrence's forward_return matches the
    exact value ``compute_forward_outcomes_for_horizons`` (Signal Research's
    own function) computes for the same occurrence -- reused, not reinvented.
    """
    storage_root = tmp_path / "workspace"
    bars = _synthetic_bars()
    signal_model = _breakout_signal_model(direction=SignalDirection.SHORT)
    spec = _signal_occurrences_study(direction=SignalDirection.SHORT)
    occurrences = _occurrences_for(direction=SignalDirection.SHORT, bars=bars)
    assert occurrences.height == 19
    assert set(occurrences.get_column("direction").unique().to_list()) == {"short"}

    # A full OHLCV frame, exactly like build_predictive_dataset's own
    # run_analysis call: evaluate_models' own frame is scoped to the signal
    # model's expression dependencies only (a MarketFieldReference(CLOSE)
    # condition requests "close" alone, not "high"/"low" too).
    analysis = run_analysis(
        RunAnalysisRequest(
            dataset_ref=spec.dataset_ref,
            timeframe=spec.dataset_ref.dataset_id.timeframe,
            requested_range=spec.time_range,
            storage_root=storage_root,
            component_requests=(),
            frame_request=AnalysisFrameRequest(),
            evaluation_timeframe=spec.evaluation_timeframe,
            preloaded_bars=bars,
        )
    )
    frame = analysis.frame
    assert frame is not None
    ohlcv = {name: frame.columns[name] for name in ("high", "low", "close")}
    expected_outcomes = compute_forward_outcomes_for_horizons(
        occurrences,
        frame=frame,
        ohlcv=ohlcv,
        horizons=(5,),
        definition=ForwardOutcomeDefinition(horizon_bars=5),
    )
    expected_by_occurrence = {
        row["occurrence_id"]: row["forward_return"]
        for row in expected_outcomes.filter(pl.col("outcome_status") == "complete").iter_rows(
            named=True
        )
    }
    assert expected_by_occurrence
    assert all(value < 0.0 for value in expected_by_occurrence.values())

    result = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=spec,
            storage_root=storage_root,
            persist=False,
            preloaded_bars=bars,
            signal_model=signal_model,
        )
    )
    actual_by_entity = {
        row["entity_id"]: row["forward_return"]
        for row in result.envelope.features.iter_rows(named=True)
    }
    assert set(expected_by_occurrence).issubset(set(actual_by_entity))
    for occurrence_id, expected_return in expected_by_occurrence.items():
        assert actual_by_entity[occurrence_id] == pytest.approx(expected_return)


def test_signal_occurrences_label_end_at_matches_every_bar_build(tmp_path: Path) -> None:
    """D-S056-05/SPRINT_056.md sec8 AC5: filter-late is structural, asserted directly.

    ``label_end_at`` for a bar present in BOTH builds must be IDENTICAL --
    the concrete test of the guarantee that ``signal_occurrences`` never
    derives ``label_end_at`` from an already-filtered sequence.
    """
    storage_root = tmp_path / "workspace"
    bars = _synthetic_bars()
    signal_model = _breakout_signal_model(direction=SignalDirection.LONG)
    every_bar_spec = _study(fold_count=1)
    signal_spec = _signal_occurrences_study(direction=SignalDirection.LONG)

    every_bar_result = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=every_bar_spec,
            storage_root=storage_root / "every_bar",
            persist=False,
            preloaded_bars=bars,
        )
    )
    signal_result = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=signal_spec,
            storage_root=storage_root / "signal_occurrences",
            persist=False,
            preloaded_bars=bars,
            signal_model=signal_model,
        )
    )

    every_bar_end_by_detected_at = {
        row["detected_at"]: row["label_end_at"]
        for row in every_bar_result.envelope.features.iter_rows(named=True)
    }
    shared = 0
    for row in signal_result.envelope.features.iter_rows(named=True):
        detected_at = row["detected_at"]
        if detected_at not in every_bar_end_by_detected_at:
            continue
        shared += 1
        assert row["label_end_at"] == every_bar_end_by_detected_at[detected_at]
    assert shared > 0
