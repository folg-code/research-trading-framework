"""Leakage regression suite for Predictive Research (SPRINT_039 §9).

Each guard has a production assertion and a counter-fixture that the checker
detects. Removing the production guard must fail the production assertion.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from tests.unit.application.predictive_research.test_build_predictive_dataset import (
    _study as _e2e_study,
)
from tests.unit.application.predictive_research.test_build_predictive_dataset import (
    _synthetic_bars as _e2e_bars,
)
from tests.unit.research.datasets.test_predictive_fingerprint import (
    _output_ref,
)
from tests.unit.research.datasets.test_predictive_fingerprint import (
    _study as _fingerprint_study,
)
from tests.unit.research.predictive.test_matrix import _build, _timestamps
from tests.unit.research.predictive.test_splitting import (
    _as_datetime,
    _assignment_key,
    _embargo_reused_as_train,
    _fold_0_test_end,
    _labelled_rows,
    _planner_spec,
    _test_windows_overlap,
    _train_label_overlaps_test,
)
from trading_framework.application.predictive_research import (
    BuildPredictiveDatasetRequest,
    build_predictive_dataset,
)
from trading_framework.research.datasets.predictive import (
    PredictiveDatasetRepository,
    compute_dataset_fingerprint,
)
from trading_framework.research.outcomes.definition import OutcomeStatus
from trading_framework.research.predictive import (
    FoldRole,
    LabelKind,
    LabelSpec,
    PredictiveMatrixError,
    assign_purged_walk_forward_folds,
)
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe


def _feature_available_after_detected(frame: pl.DataFrame) -> bool:
    if frame.height == 0:
        return False
    return frame.filter(pl.col("available_at") > pl.col("detected_at")).height > 0


def _has_non_complete_labelled_row(frame: pl.DataFrame) -> bool:
    return (
        frame.filter(
            (pl.col("outcome_status") != OutcomeStatus.COMPLETE.value)
            & pl.col("label").is_not_null()
        ).height
        > 0
    )


def _fingerprint_including_created_at(
    fingerprint: str,
    created_at_utc: datetime,
) -> str:
    payload = {
        "dataset_fingerprint": fingerprint,
        "created_at_utc": created_at_utc.isoformat(),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _fingerprint_from_dataset_ref_only(dataset_ref: object) -> str:
    return hashlib.sha256(str(dataset_ref).encode("utf-8")).hexdigest()


def test_no_feature_available_at_later_than_detected_at() -> None:
    close = (100.0, 101.0, 102.0, 103.0, 104.0)
    timestamps = _timestamps(len(close))
    feature_values = (1.0, 1.0, 1.0, 1.0, 1.0)
    label = LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("1m"))
    valid = _build(
        close=close,
        feature_values=feature_values,
        label=label,
        horizon_bars=1,
    )
    equal_available = _build(
        close=close,
        feature_values=feature_values,
        label=label,
        horizon_bars=1,
        available_at=timestamps,
    )
    late_available = tuple(timestamp + timedelta(minutes=1) for timestamp in timestamps)
    mixed_late = (timestamps[0] + timedelta(minutes=1), *timestamps[1:])

    assert not _feature_available_after_detected(valid.rows)
    assert not _feature_available_after_detected(equal_available.rows)
    with pytest.raises(
        PredictiveMatrixError,
        match="feature available_at must not be later than detected_at",
    ):
        _build(
            close=close,
            feature_values=feature_values,
            label=label,
            horizon_bars=1,
            available_at=late_available,
        )
    with pytest.raises(
        PredictiveMatrixError,
        match="feature available_at must not be later than detected_at",
    ):
        _build(
            close=close,
            feature_values=feature_values,
            label=label,
            horizon_bars=1,
            available_at=mixed_late,
        )

    leaked = valid.rows.with_columns(
        (pl.col("detected_at") + pl.duration(minutes=1)).alias("available_at")
    )
    assert _feature_available_after_detected(leaked)


def test_no_train_row_has_label_end_inside_same_fold_test_window() -> None:
    spec = _planner_spec()
    assigned = assign_purged_walk_forward_folds(
        _labelled_rows(count=12, horizon_minutes=2),
        spec,
    )

    assert not _train_label_overlaps_test(assigned, spec)

    leaked = assigned.with_columns(
        pl.when(pl.col("fold_role") == FoldRole.PURGED.value)
        .then(pl.lit(FoldRole.TRAIN.value))
        .otherwise(pl.col("fold_role"))
        .alias("fold_role")
    )
    assert _train_label_overlaps_test(leaked, spec)


def test_expanding_embargo_holds_out_span_after_each_test_window() -> None:
    spec = _planner_spec(embargo_span="2m", min_train_rows=1)
    assigned = assign_purged_walk_forward_folds(
        _labelled_rows(count=16, horizon_minutes=1),
        spec,
    )
    fold_0_test_end = _fold_0_test_end(assigned)
    embargo_end = fold_0_test_end + timedelta(minutes=2)
    fold_0_embargo = assigned.filter(
        (pl.col("fold_id") == 0)
        & (pl.col("fold_role") == FoldRole.EMBARGOED.value)
        & (pl.col("available_at") > fold_0_test_end)
        & (pl.col("available_at") <= embargo_end)
    )
    later_train_on_embargo = assigned.filter(
        (pl.col("fold_id") == 1)
        & (pl.col("fold_role") == FoldRole.TRAIN.value)
        & (pl.col("available_at") > fold_0_test_end)
        & (pl.col("available_at") <= embargo_end)
    )

    assert spec.mode.value == "EXPANDING"
    assert fold_0_embargo.height > 0
    assert later_train_on_embargo.height == 0
    assert not _embargo_reused_as_train(assigned, spec)

    leaked = assigned.with_columns(
        pl.when(
            (pl.col("fold_id") == 1)
            & (pl.col("available_at") > fold_0_test_end)
            & (pl.col("available_at") <= embargo_end)
        )
        .then(pl.lit(FoldRole.TRAIN.value))
        .otherwise(pl.col("fold_role"))
        .alias("fold_role")
    )
    assert _embargo_reused_as_train(leaked, spec)


def test_non_complete_outcome_rows_never_receive_a_label() -> None:
    close = (100.0, 101.0, 102.0, 103.0, 104.0)
    matrix = _build(
        close=close,
        feature_values=(1.0, 1.0, 1.0, 1.0, 1.0),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("3m")),
        horizon_bars=3,
    )

    assert matrix.exclusions.incomplete_horizon > 0
    assert set(matrix.rows.get_column("outcome_status").to_list()) == {OutcomeStatus.COMPLETE.value}
    assert not _has_non_complete_labelled_row(matrix.rows)

    leaked = matrix.rows.with_columns(
        pl.when(pl.int_range(pl.len()) == 0)
        .then(pl.lit(OutcomeStatus.INCOMPLETE_HORIZON.value))
        .otherwise(pl.col("outcome_status"))
        .alias("outcome_status")
    )
    assert _has_non_complete_labelled_row(leaked)


def test_fold_test_windows_are_chronological_and_non_overlapping() -> None:
    assigned = assign_purged_walk_forward_folds(
        _labelled_rows(count=12, horizon_minutes=2),
        _planner_spec(),
    )
    tests = assigned.filter(pl.col("fold_role") == FoldRole.TEST.value)
    fold_starts = [
        _as_datetime(tests.filter(pl.col("fold_id") == fold_id).get_column("available_at").min())
        for fold_id in (0, 1)
    ]

    assert fold_starts[0] < fold_starts[1]
    assert not _test_windows_overlap(assigned)

    overlapping = pl.concat(
        [
            assigned,
            tests.filter(pl.col("fold_id") == 0).with_columns(
                pl.lit(1).cast(pl.Int64).alias("fold_id")
            ),
        ]
    )
    assert _test_windows_overlap(overlapping)


def test_shuffling_input_row_order_does_not_change_fold_assignment() -> None:
    rows = _labelled_rows(count=12, horizon_minutes=2)
    spec = _planner_spec()
    shuffled = rows.sample(fraction=1.0, shuffle=True, seed=7)

    assert shuffled.get_column("entity_id").to_list() != rows.get_column("entity_id").to_list()

    assigned = assign_purged_walk_forward_folds(rows, spec)
    shuffled_assigned = assign_purged_walk_forward_folds(shuffled, spec)

    assert _assignment_key(assigned).equals(_assignment_key(shuffled_assigned))

    order_dependent = shuffled.with_row_index("row_index").with_columns(
        (pl.col("row_index") % 2).cast(pl.Int64).alias("fold_id"),
        pl.when(pl.col("row_index") < 6)
        .then(pl.lit(FoldRole.TRAIN.value))
        .otherwise(pl.lit(FoldRole.TEST.value))
        .alias("fold_role"),
    )
    assert not _assignment_key(assigned).equals(
        order_dependent.select("entity_id", "horizon_bars", "fold_id", "fold_role").sort(
            "fold_id", "entity_id", "horizon_bars"
        )
    )


def test_rebuild_from_same_spec_produces_identical_fingerprint(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    spec = _e2e_study()
    bars = _e2e_bars()
    first = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=spec,
            storage_root=storage_root,
            persist=True,
            preloaded_bars=bars,
            clock=FixedClock(datetime(2024, 6, 1, 12, 0, tzinfo=UTC)),
        )
    )
    loaded = PredictiveDatasetRepository(storage_root).read(first.dataset_ref)
    second = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=spec,
            storage_root=storage_root,
            persist=False,
            preloaded_bars=bars,
            clock=FixedClock(datetime(2024, 6, 2, 12, 0, tzinfo=UTC)),
        )
    )
    lineage = {"atr_14": _output_ref()}
    fingerprint_spec = _fingerprint_study()
    definition_hash = fingerprint_spec.definition_hash or ""
    unit_first = compute_dataset_fingerprint(
        definition_hash=definition_hash,
        feature_lineage=lineage,
        dataset_ref=fingerprint_spec.dataset_ref,
        time_range=fingerprint_spec.time_range,
    )
    unit_second = compute_dataset_fingerprint(
        definition_hash=definition_hash,
        feature_lineage=lineage,
        dataset_ref=fingerprint_spec.dataset_ref,
        time_range=fingerprint_spec.time_range,
    )

    assert first.fingerprint == second.fingerprint
    assert loaded.manifest.dataset_fingerprint == first.fingerprint
    assert loaded.features.height == first.envelope.features.height
    assert unit_first == unit_second
    assert _fingerprint_including_created_at(
        first.fingerprint,
        first.envelope.manifest.created_at_utc,
    ) != _fingerprint_including_created_at(
        second.fingerprint,
        second.envelope.manifest.created_at_utc,
    )


def test_spec_change_produces_a_different_fingerprint(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    bars = _e2e_bars()
    baseline = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=_e2e_study(fold_count=2),
            storage_root=storage_root,
            persist=False,
            preloaded_bars=bars,
        )
    )
    changed = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=_e2e_study(fold_count=1),
            storage_root=storage_root,
            persist=False,
            preloaded_bars=bars,
        )
    )
    fingerprint_baseline = _fingerprint_study()
    fingerprint_changed = _fingerprint_study(fold_count=3)
    fingerprint_relabelled = _fingerprint_study(
        label=LabelSpec(kind=LabelKind.BINARY, horizon=Timeframe("5m"), threshold=0.0)
    )
    fingerprint_renamed = _fingerprint_study(alias="atr_21")
    lineage = {"atr_14": _output_ref()}
    unit_baseline = compute_dataset_fingerprint(
        definition_hash=fingerprint_baseline.definition_hash or "",
        feature_lineage=lineage,
        dataset_ref=fingerprint_baseline.dataset_ref,
        time_range=fingerprint_baseline.time_range,
    )
    unit_changed = compute_dataset_fingerprint(
        definition_hash=fingerprint_changed.definition_hash or "",
        feature_lineage=lineage,
        dataset_ref=fingerprint_changed.dataset_ref,
        time_range=fingerprint_changed.time_range,
    )
    unit_relabelled = compute_dataset_fingerprint(
        definition_hash=fingerprint_relabelled.definition_hash or "",
        feature_lineage=lineage,
        dataset_ref=fingerprint_relabelled.dataset_ref,
        time_range=fingerprint_relabelled.time_range,
    )
    unit_renamed = compute_dataset_fingerprint(
        definition_hash=fingerprint_renamed.definition_hash or "",
        feature_lineage={"atr_21": _output_ref()},
        dataset_ref=fingerprint_renamed.dataset_ref,
        time_range=fingerprint_renamed.time_range,
    )

    assert changed.fingerprint != baseline.fingerprint
    assert unit_changed != unit_baseline
    assert unit_relabelled != unit_baseline
    assert unit_renamed != unit_baseline
    assert _fingerprint_from_dataset_ref_only(
        baseline.envelope.manifest.source_dataset_ref
    ) == _fingerprint_from_dataset_ref_only(changed.envelope.manifest.source_dataset_ref)
