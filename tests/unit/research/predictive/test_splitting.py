"""Unit tests for purged walk-forward split spec and fold-role planner."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import pairwise

import polars as pl
import pytest

from trading_framework.research.predictive import (
    FoldRole,
    PredictiveMatrixError,
    PredictiveSpecError,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    assign_purged_walk_forward_folds,
)
from trading_framework.time.models.timeframe import Timeframe

_UTC = pl.Datetime(time_unit="us", time_zone="UTC")


def _valid_split() -> PurgedWalkForwardSplitSpec:
    return PurgedWalkForwardSplitSpec(
        mode=PurgedWalkForwardSplitMode.EXPANDING,
        fold_count=4,
        test_span=Timeframe("20d"),
        embargo_span=Timeframe("15m"),
        min_train_rows=500,
    )


def test_split_spec_is_valid() -> None:
    spec = _valid_split()

    assert spec.mode is PurgedWalkForwardSplitMode.EXPANDING
    assert spec.fold_count == 4
    assert spec.embargo_span.value == "15m"


def test_zero_embargo_span_is_allowed() -> None:
    spec = PurgedWalkForwardSplitSpec(
        mode=PurgedWalkForwardSplitMode.ROLLING,
        fold_count=2,
        test_span=Timeframe("5d"),
        embargo_span=Timeframe("0m"),
        min_train_rows=1,
    )

    assert spec.embargo_span.total_seconds == 0


def test_fold_count_must_be_positive() -> None:
    with pytest.raises(PredictiveSpecError, match="fold_count must be at least 1"):
        PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.ROLLING,
            fold_count=0,
            test_span=Timeframe("5d"),
            embargo_span=Timeframe("15m"),
            min_train_rows=10,
        )


def test_min_train_rows_must_be_positive() -> None:
    with pytest.raises(PredictiveSpecError, match="min_train_rows must be at least 1"):
        PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.ROLLING,
            fold_count=2,
            test_span=Timeframe("5d"),
            embargo_span=Timeframe("15m"),
            min_train_rows=0,
        )


def test_test_span_must_be_positive() -> None:
    with pytest.raises(PredictiveSpecError, match="test_span must be a positive duration"):
        PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.ROLLING,
            fold_count=2,
            test_span=Timeframe("0m"),
            embargo_span=Timeframe("15m"),
            min_train_rows=10,
        )


def test_split_spec_dict_round_trip() -> None:
    original = _valid_split()

    restored = PurgedWalkForwardSplitSpec.from_dict(original.to_dict())

    assert restored == original


def test_split_mode_is_the_declared_set() -> None:
    assert {member.value for member in PurgedWalkForwardSplitMode} == {
        "ROLLING",
        "EXPANDING",
    }


def test_invalid_split_mode_is_rejected() -> None:
    payload = _valid_split().to_dict()
    payload["mode"] = "K_FOLD"

    with pytest.raises(PredictiveSpecError, match="invalid split mode"):
        PurgedWalkForwardSplitSpec.from_dict(payload)


def test_split_spans_reject_tick() -> None:
    with pytest.raises(PredictiveSpecError, match="test_span must be a bar duration"):
        PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.ROLLING,
            fold_count=2,
            test_span=Timeframe("tick"),
            embargo_span=Timeframe("15m"),
            min_train_rows=10,
        )

    with pytest.raises(PredictiveSpecError, match="embargo_span must be a bar duration"):
        PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.ROLLING,
            fold_count=2,
            test_span=Timeframe("5d"),
            embargo_span=Timeframe("tick"),
            min_train_rows=10,
        )


def test_fold_count_rejects_boolean() -> None:
    payload = _valid_split().to_dict()
    payload["fold_count"] = True

    with pytest.raises(PredictiveSpecError, match="fold_count must be an integer"):
        PurgedWalkForwardSplitSpec.from_dict(payload)


def test_split_spec_from_dict_rejects_missing_field() -> None:
    payload = _valid_split().to_dict()
    del payload["test_span"]

    with pytest.raises(PredictiveSpecError, match="missing field: test_span"):
        PurgedWalkForwardSplitSpec.from_dict(payload)


def _labelled_rows(*, count: int, horizon_minutes: int) -> pl.DataFrame:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    available = [start + timedelta(minutes=index) for index in range(count)]
    return pl.DataFrame(
        {
            "entity_id": [timestamp.isoformat() for timestamp in available],
            "horizon_bars": [horizon_minutes] * count,
            "detected_at": available,
            "available_at": available,
            "label_end_at": [
                timestamp + timedelta(minutes=horizon_minutes) for timestamp in available
            ],
            "label": [0.0] * count,
        },
        schema={
            "entity_id": pl.String(),
            "horizon_bars": pl.Int64(),
            "detected_at": _UTC,
            "available_at": _UTC,
            "label_end_at": _UTC,
            "label": pl.Float64(),
        },
    )


def _planner_spec(
    *,
    mode: PurgedWalkForwardSplitMode = PurgedWalkForwardSplitMode.EXPANDING,
    fold_count: int = 2,
    test_span: str = "2m",
    embargo_span: str = "0m",
    min_train_rows: int = 1,
) -> PurgedWalkForwardSplitSpec:
    return PurgedWalkForwardSplitSpec(
        mode=mode,
        fold_count=fold_count,
        test_span=Timeframe(test_span),
        embargo_span=Timeframe(embargo_span),
        min_train_rows=min_train_rows,
    )


def _as_datetime(value: object) -> datetime:
    if not isinstance(value, datetime):
        msg = f"expected datetime, got {type(value)!r}"
        raise TypeError(msg)
    return value


def _assignment_key(frame: pl.DataFrame) -> pl.DataFrame:
    return frame.select("entity_id", "horizon_bars", "fold_id", "fold_role").sort(
        "fold_id", "entity_id", "horizon_bars"
    )


def _train_label_overlaps_test(assigned: pl.DataFrame, spec: PurgedWalkForwardSplitSpec) -> bool:
    test_span = timedelta(seconds=spec.test_span.total_seconds)
    fold_ids = assigned.get_column("fold_id").unique().sort().to_list()
    for fold_id in fold_ids:
        fold = assigned.filter(pl.col("fold_id") == fold_id)
        test_times = fold.filter(pl.col("fold_role") == FoldRole.TEST.value).get_column(
            "available_at"
        )
        if test_times.len() == 0:
            continue
        test_end = _as_datetime(test_times.max())
        test_lower = test_end - test_span
        leaked = fold.filter(
            (pl.col("fold_role") == FoldRole.TRAIN.value)
            & (pl.col("label_end_at") > test_lower)
            & (pl.col("label_end_at") <= test_end)
        )
        if leaked.height > 0:
            return True
    return False


def _test_windows_overlap(assigned: pl.DataFrame) -> bool:
    tests = assigned.filter(pl.col("fold_role") == FoldRole.TEST.value)
    seen: dict[datetime, int] = {}
    for fold_id, timestamp in zip(
        tests.get_column("fold_id").to_list(),
        tests.get_column("available_at").to_list(),
        strict=True,
    ):
        previous = seen.get(timestamp)
        if previous is not None and previous != fold_id:
            return True
        seen[timestamp] = fold_id
    ranges: list[tuple[datetime, datetime]] = []
    for fold_id in tests.get_column("fold_id").unique().sort().to_list():
        times = tests.filter(pl.col("fold_id") == fold_id).get_column("available_at")
        start, end = _as_datetime(times.min()), _as_datetime(times.max())
        ranges.append((start, end))
    chronological = sorted(ranges, key=lambda item: item[0])
    for previous_range, current_range in pairwise(chronological):
        if previous_range[1] >= current_range[0]:
            return True
    return False


def _embargo_reused_as_train(assigned: pl.DataFrame, spec: PurgedWalkForwardSplitSpec) -> bool:
    embargo_span = timedelta(seconds=spec.embargo_span.total_seconds)
    if embargo_span.total_seconds() == 0:
        return False
    tests = assigned.filter(pl.col("fold_role") == FoldRole.TEST.value)
    fold_ids = tests.get_column("fold_id").unique().sort().to_list()
    for fold_id in fold_ids:
        test_end = _as_datetime(
            tests.filter(pl.col("fold_id") == fold_id).get_column("available_at").max()
        )
        embargo_end = test_end + embargo_span
        later_train = assigned.filter(
            (pl.col("fold_id") > fold_id)
            & (pl.col("fold_role") == FoldRole.TRAIN.value)
            & (pl.col("available_at") > test_end)
            & (pl.col("available_at") <= embargo_end)
        )
        if later_train.height > 0:
            return True
    return False


def test_assign_folds_is_long_format_with_persisted_roles() -> None:
    assigned = assign_purged_walk_forward_folds(
        _labelled_rows(count=12, horizon_minutes=2),
        _planner_spec(),
    )

    assert assigned.get_column("fold_id").unique().sort().to_list() == [0, 1]
    assert set(assigned.get_column("fold_role").unique().to_list()) <= {
        FoldRole.TRAIN.value,
        FoldRole.TEST.value,
        FoldRole.PURGED.value,
        FoldRole.EMBARGOED.value,
    }
    assert assigned.select("entity_id", "horizon_bars", "fold_id").height == assigned.height


def test_train_label_end_never_falls_inside_same_fold_test_window() -> None:
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


def test_test_windows_are_chronological_and_non_overlapping() -> None:
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


def test_expanding_embargo_holds_out_span_after_test() -> None:
    spec = _planner_spec(embargo_span="2m", min_train_rows=1)
    assigned = assign_purged_walk_forward_folds(
        _labelled_rows(count=16, horizon_minutes=1),
        spec,
    )
    fold_0_test_end = _as_datetime(
        assigned.filter((pl.col("fold_id") == 0) & (pl.col("fold_role") == FoldRole.TEST.value))
        .get_column("available_at")
        .max()
    )
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


def test_shuffling_input_rows_does_not_change_fold_assignment() -> None:
    rows = _labelled_rows(count=12, horizon_minutes=2)
    spec = _planner_spec()
    shuffled = rows.sample(fraction=1.0, shuffle=True, seed=7)

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


def test_rolling_train_window_drops_early_rows_that_expanding_keeps() -> None:
    rows = _labelled_rows(count=12, horizon_minutes=2)
    expanding = assign_purged_walk_forward_folds(
        rows,
        _planner_spec(mode=PurgedWalkForwardSplitMode.EXPANDING),
    )
    rolling = assign_purged_walk_forward_folds(
        rows,
        _planner_spec(mode=PurgedWalkForwardSplitMode.ROLLING),
    )
    expanding_fold_1 = set(
        expanding.filter((pl.col("fold_id") == 1) & (pl.col("fold_role") == FoldRole.TRAIN.value))
        .get_column("entity_id")
        .to_list()
    )
    rolling_fold_1 = set(
        rolling.filter((pl.col("fold_id") == 1) & (pl.col("fold_role") == FoldRole.TRAIN.value))
        .get_column("entity_id")
        .to_list()
    )
    first_entity = rows.get_column("entity_id").to_list()[0]

    assert first_entity in expanding_fold_1
    assert first_entity not in rolling_fold_1
    assert rolling_fold_1 < expanding_fold_1


def test_insufficient_train_rows_after_purge_raises() -> None:
    with pytest.raises(PredictiveMatrixError, match="min_train_rows is 50"):
        assign_purged_walk_forward_folds(
            _labelled_rows(count=12, horizon_minutes=2),
            _planner_spec(min_train_rows=50),
        )


def test_missing_availability_columns_raise() -> None:
    rows = _labelled_rows(count=8, horizon_minutes=1).drop("label_end_at")

    with pytest.raises(PredictiveMatrixError, match="missing required column: label_end_at"):
        assign_purged_walk_forward_folds(rows, _planner_spec())


def test_series_too_short_for_declared_folds_raises() -> None:
    with pytest.raises(PredictiveMatrixError, match="too short to place 2 test windows"):
        assign_purged_walk_forward_folds(
            _labelled_rows(count=3, horizon_minutes=1),
            _planner_spec(),
        )
