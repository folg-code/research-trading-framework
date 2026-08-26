"""Unit tests for the labelled Predictive Research feature-matrix builder."""

from __future__ import annotations

import ast
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

import trading_framework
from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis.assembly.frame import AnalysisFrame
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
from trading_framework.research.outcomes.definition import OutcomeStatus
from trading_framework.research.predictive import (
    FeatureMatrixSpec,
    FeatureSpec,
    FeatureTransform,
    LabelKind,
    LabelledFeatureMatrix,
    LabelSpec,
    PredictiveMatrixError,
    build_labelled_feature_matrix,
)
from trading_framework.time.models.timeframe import Timeframe

_PREDICTIVE_ROOT = Path(trading_framework.__file__).resolve().parent / "research" / "predictive"
_ML_LIBRARY_ROOTS = ("sklearn", "xgboost", "lightgbm", "catboost", "torch")


def _timestamps(count: int) -> tuple[datetime, ...]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    return tuple(start + timedelta(minutes=index) for index in range(count))


def _ohlcv_from_close(close: tuple[float, ...]) -> dict[str, tuple[float, ...]]:
    return {"open": close, "high": close, "low": close, "close": close, "volume": close}


def _feature(
    *,
    alias: str = "atr_14",
    transform: FeatureTransform = FeatureTransform.NONE,
) -> FeatureSpec:
    return FeatureSpec(
        component_id=ComponentId("volatility.atr"),
        parameters=CanonicalParameters.from_mapping({"period": 14}),
        output_id=OutputId("atr"),
        alias=alias,
        transform=transform,
    )


def _frame(
    *,
    timestamps: tuple[datetime, ...],
    feature_values: tuple[float, ...],
    alias: str = "atr_14",
) -> AnalysisFrame:
    return AnalysisFrame(
        timestamps=timestamps,
        columns={alias: feature_values},
        column_lineage={},
    )


def _build(
    *,
    close: tuple[float, ...],
    feature_values: tuple[float, ...],
    label: LabelSpec,
    horizon_bars: int,
    transform: FeatureTransform = FeatureTransform.NONE,
    alias: str = "atr_14",
    available_at: tuple[datetime, ...] | None = None,
) -> LabelledFeatureMatrix:
    timestamps = _timestamps(len(close))
    return build_labelled_feature_matrix(
        frame=_frame(timestamps=timestamps, feature_values=feature_values, alias=alias),
        ohlcv=_ohlcv_from_close(close),
        features=FeatureMatrixSpec(features=(_feature(alias=alias, transform=transform),)),
        label=label,
        horizon_bars=horizon_bars,
        available_at=available_at,
    )


def test_regression_labels_use_complete_forward_returns() -> None:
    close = (100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0)
    matrix = _build(
        close=close,
        feature_values=tuple(float(index) for index in range(len(close))),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("3m")),
        horizon_bars=3,
    )

    assert matrix.exclusions.labelled_rows == 5
    assert matrix.exclusions.incomplete_horizon == 3
    first = matrix.rows.row(0, named=True)
    assert first["label"] == pytest.approx(close[3] / close[0] - 1.0)
    assert first["forward_return"] == pytest.approx(first["label"])
    last = matrix.rows.row(-1, named=True)
    assert last["label"] == pytest.approx(close[7] / close[4] - 1.0)
    assert last["forward_return"] == pytest.approx(last["label"])


def test_binary_and_ternary_labels_from_forward_return() -> None:
    close = (100.0, 100.0, 101.0, 100.0, 99.0, 99.0, 100.0, 98.0)
    feature_values = tuple(1.0 for _ in close)
    horizon_bars = 2

    binary = _build(
        close=close,
        feature_values=feature_values,
        label=LabelSpec(kind=LabelKind.BINARY, horizon=Timeframe("2m"), threshold=0.0),
        horizon_bars=horizon_bars,
    )
    ternary = _build(
        close=close,
        feature_values=feature_values,
        label=LabelSpec(kind=LabelKind.TERNARY, horizon=Timeframe("2m"), neutral_band=0.005),
        horizon_bars=horizon_bars,
    )

    binary_labels = binary.rows.get_column("label").to_list()
    ternary_labels = ternary.rows.get_column("label").to_list()
    binary_returns = binary.rows.get_column("forward_return").to_list()
    assert binary.exclusions.labelled_rows == 6
    assert binary_labels[0] == 1.0  # 101/100 - 1 > 0
    assert binary_labels[1] == 0.0  # 100/100 - 1 == 0
    assert binary_labels[2] == 0.0  # 99/101 - 1 < 0
    assert binary_returns[0] == pytest.approx(101.0 / 100.0 - 1.0)
    assert binary_returns[1] == pytest.approx(0.0)
    assert binary_labels[0] != binary_returns[0]
    assert ternary_labels[0] == 1.0
    assert ternary_labels[1] == 0.0
    assert ternary_labels[2] == -1.0
    assert ternary.rows.get_column("forward_return").to_list()[2] != ternary_labels[2]


def test_incomplete_horizon_rows_are_excluded_and_counted() -> None:
    close = (100.0, 101.0, 102.0, 103.0, 104.0)
    matrix = _build(
        close=close,
        feature_values=(1.0, 1.0, 1.0, 1.0, 1.0),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("2m")),
        horizon_bars=2,
    )

    assert matrix.exclusions.candidate_rows == 5
    assert matrix.exclusions.labelled_rows == 3
    assert matrix.exclusions.incomplete_horizon == 2
    assert matrix.exclusions.insufficient_data == 0
    assert matrix.exclusions.null_features == 0
    assert matrix.rows.height == 3
    assert "fold_role" not in matrix.rows.columns


def test_null_and_non_finite_features_are_excluded_and_counted() -> None:
    close = (100.0, 101.0, 102.0, 103.0, 104.0, 105.0)
    matrix = _build(
        close=close,
        feature_values=(1.0, math.nan, math.inf, 4.0, 5.0, 6.0),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("2m")),
        horizon_bars=2,
    )

    assert matrix.exclusions.labelled_rows == 2
    assert matrix.exclusions.null_features == 2
    assert matrix.exclusions.incomplete_horizon == 2
    assert matrix.rows.get_column("atr_14").to_list() == [1.0, 4.0]


def test_label_end_at_equals_timestamp_horizon_bars_ahead() -> None:
    close = (100.0, 101.0, 102.0, 103.0, 104.0, 105.0)
    timestamps = _timestamps(len(close))
    matrix = _build(
        close=close,
        feature_values=tuple(1.0 for _ in close),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("2m")),
        horizon_bars=2,
    )

    ends = [_as_utc(value) for value in matrix.rows.get_column("label_end_at").to_list()]
    detected = [_as_utc(value) for value in matrix.rows.get_column("detected_at").to_list()]
    assert ends[0] == timestamps[2]
    assert ends[-1] == timestamps[5]
    for detected_at, label_end_at in zip(detected, ends, strict=True):
        bar_index = timestamps.index(detected_at)
        assert label_end_at == timestamps[bar_index + 2]


def test_no_labelled_row_has_non_complete_outcome_status() -> None:
    close = (100.0, 101.0, 102.0, 103.0, 104.0)
    matrix = _build(
        close=close,
        feature_values=(1.0, 1.0, 1.0, 1.0, 1.0),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("3m")),
        horizon_bars=3,
    )

    statuses = set(matrix.rows.get_column("outcome_status").to_list())
    assert statuses == {OutcomeStatus.COMPLETE.value}
    assert matrix.exclusions.incomplete_horizon == 3


def test_missing_feature_alias_raises() -> None:
    timestamps = _timestamps(4)
    close = (100.0, 101.0, 102.0, 103.0)
    frame = AnalysisFrame(
        timestamps=timestamps,
        columns={"other": (1.0, 1.0, 1.0, 1.0)},
        column_lineage={},
    )

    with pytest.raises(PredictiveMatrixError, match="declared feature alias is not present"):
        build_labelled_feature_matrix(
            frame=frame,
            ohlcv=_ohlcv_from_close(close),
            features=FeatureMatrixSpec(features=(_feature(),)),
            label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("1m")),
            horizon_bars=1,
        )


def test_diff_transform_is_causal() -> None:
    close = (100.0, 101.0, 102.0, 103.0, 104.0, 105.0)
    raw = (10.0, 12.0, 15.0, 19.0, 24.0, 30.0)
    matrix = _build(
        close=close,
        feature_values=raw,
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("2m")),
        horizon_bars=2,
        transform=FeatureTransform.DIFF,
    )

    diffs = matrix.rows.get_column("atr_14").to_list()
    assert matrix.exclusions.null_features == 1
    assert diffs[0] == pytest.approx(raw[1] - raw[0])
    assert diffs[1] == pytest.approx(raw[2] - raw[1])
    assert diffs[2] == pytest.approx(raw[3] - raw[2])
    # DIFF[t] must not look at t+1: the next raw value is 24, not used at t=2.
    assert diffs[2] != pytest.approx(raw[4] - raw[2])


def test_log_transform_is_applied_after_column_resolve() -> None:
    close = (100.0, 101.0, 102.0, 103.0, 104.0)
    raw = (math.e, math.e**2, math.e, math.e**2, math.e)
    matrix = _build(
        close=close,
        feature_values=raw,
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("1m")),
        horizon_bars=1,
        transform=FeatureTransform.LOG,
    )

    logs = matrix.rows.get_column("atr_14").to_list()
    assert logs[0] == pytest.approx(1.0)
    assert logs[1] == pytest.approx(2.0)


def test_rank_transform_is_rejected() -> None:
    close = (100.0, 101.0, 102.0, 103.0)
    with pytest.raises(PredictiveMatrixError, match="RANK transform is not supported"):
        _build(
            close=close,
            feature_values=(1.0, 2.0, 3.0, 4.0),
            label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("1m")),
            horizon_bars=1,
            transform=FeatureTransform.RANK,
        )


def test_available_at_defaults_to_bar_timestamp() -> None:
    close = (100.0, 101.0, 102.0, 103.0)
    timestamps = _timestamps(len(close))
    matrix = _build(
        close=close,
        feature_values=(1.0, 1.0, 1.0, 1.0),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("1m")),
        horizon_bars=1,
    )

    detected = [_as_utc(value) for value in matrix.rows.get_column("detected_at").to_list()]
    available = [_as_utc(value) for value in matrix.rows.get_column("available_at").to_list()]
    assert detected == available
    assert detected[0] == timestamps[0]


def test_explicit_available_at_is_preserved() -> None:
    close = (100.0, 101.0, 102.0, 103.0)
    timestamps = _timestamps(len(close))
    available_at = tuple(timestamp - timedelta(seconds=30) for timestamp in timestamps)
    matrix = _build(
        close=close,
        feature_values=(1.0, 1.0, 1.0, 1.0),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("1m")),
        horizon_bars=1,
        available_at=available_at,
    )

    actual = [_as_utc(value) for value in matrix.rows.get_column("available_at").to_list()]
    assert actual[0] == available_at[0]


def test_insufficient_close_is_counted() -> None:
    close = (100.0, math.nan, 102.0, 103.0, 104.0)
    matrix = _build(
        close=close,
        feature_values=(1.0, 1.0, 1.0, 1.0, 1.0),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("1m")),
        horizon_bars=1,
    )

    accounted = (
        matrix.exclusions.labelled_rows
        + matrix.exclusions.incomplete_horizon
        + matrix.exclusions.insufficient_data
        + matrix.exclusions.null_features
    )
    assert matrix.exclusions.insufficient_data >= 1
    assert accounted == matrix.exclusions.candidate_rows


def test_matrix_builder_does_not_import_ml_or_analysis_runtime() -> None:
    source = (_PREDICTIVE_ROOT / "matrix.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)

    assert not any(
        name == root or name.startswith(f"{root}.")
        for name in imported
        for root in _ML_LIBRARY_ROOTS
    )
    assert all("run_analysis" not in name for name in imported)
    assert all("signal_model" not in name for name in imported)
    assert all(
        not name.startswith("trading_framework.application.market_analysis") for name in imported
    )
    assert "trading_framework.research.outcomes.calculator" in imported
    assert "compute_forward_outcomes_for_horizons" in source


def test_pct_change_transform_is_causal() -> None:
    close = (100.0, 101.0, 102.0, 103.0, 104.0, 105.0)
    raw = (10.0, 12.0, 15.0, 20.0, 25.0, 30.0)
    matrix = _build(
        close=close,
        feature_values=raw,
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("2m")),
        horizon_bars=2,
        transform=FeatureTransform.PCT_CHANGE,
    )

    changes = matrix.rows.get_column("atr_14").to_list()
    assert matrix.exclusions.null_features == 1
    assert changes[0] == pytest.approx((raw[1] - raw[0]) / raw[0])
    assert changes[1] == pytest.approx((raw[2] - raw[1]) / raw[1])
    # PCT_CHANGE[t] must not look at t+1.
    assert changes[1] != pytest.approx((raw[3] - raw[1]) / raw[1])


def test_feature_resolves_via_column_lineage_when_alias_absent() -> None:
    close = (100.0, 101.0, 102.0, 103.0)
    timestamps = _timestamps(len(close))
    frame_column = "volatility.atr:atr"
    frame = AnalysisFrame(
        timestamps=timestamps,
        columns={frame_column: (1.5, 2.5, 3.5, 4.5)},
        column_lineage={frame_column: _atr_output_ref()},
    )

    matrix = build_labelled_feature_matrix(
        frame=frame,
        ohlcv=_ohlcv_from_close(close),
        features=FeatureMatrixSpec(features=(_feature(alias="atr_14"),)),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("1m")),
        horizon_bars=1,
    )

    assert "atr_14" in matrix.rows.columns
    assert frame_column not in matrix.rows.columns
    assert matrix.rows.get_column("atr_14").to_list() == [1.5, 2.5, 3.5]


def test_labels_come_from_compute_forward_outcomes_for_horizons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close = (100.0, 101.0, 102.0, 103.0)
    calls: list[int] = []

    def fake_compute(
        occurrences: pl.DataFrame,
        *,
        frame: AnalysisFrame,
        ohlcv: dict[str, tuple[float, ...]],
        horizons: tuple[int, ...],
        definition: object,
    ) -> pl.DataFrame:
        del frame, ohlcv, definition
        calls.append(len(occurrences))
        ids = occurrences.get_column("occurrence_id").to_list()
        horizon = horizons[0]
        row_count = len(ids)
        statuses: list[str] = []
        returns: list[float | None] = []
        for index in range(row_count):
            if index + horizon >= row_count:
                statuses.append(OutcomeStatus.INCOMPLETE_HORIZON.value)
                returns.append(None)
            else:
                statuses.append(OutcomeStatus.COMPLETE.value)
                returns.append(0.42)
        return pl.DataFrame(
            {
                "occurrence_id": ids,
                "horizon_bars": [horizon] * row_count,
                "outcome_status": statuses,
                "terminal_price": [None] * row_count,
                "forward_return": returns,
                "mfe": [None] * row_count,
                "mae": [None] * row_count,
            }
        )

    monkeypatch.setattr(
        "trading_framework.research.predictive.matrix.compute_forward_outcomes_for_horizons",
        fake_compute,
    )
    matrix = _build(
        close=close,
        feature_values=(1.0, 1.0, 1.0, 1.0),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("1m")),
        horizon_bars=1,
    )

    assert calls == [4]
    assert matrix.rows.get_column("label").to_list() == [0.42, 0.42, 0.42]
    # Distinct from close-path forward return (101/100 - 1 == 0.01).
    assert close[1] / close[0] - 1.0 != pytest.approx(0.42)


def test_incomplete_horizon_takes_precedence_over_null_features() -> None:
    close = (100.0, 101.0, 102.0, 103.0, 104.0)
    matrix = _build(
        close=close,
        feature_values=(1.0, math.nan, 3.0, math.nan, math.nan),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("2m")),
        horizon_bars=2,
    )

    assert matrix.exclusions.candidate_rows == 5
    assert matrix.exclusions.labelled_rows == 2
    assert matrix.exclusions.incomplete_horizon == 2
    assert matrix.exclusions.null_features == 1
    assert (
        matrix.exclusions.labelled_rows
        + matrix.exclusions.incomplete_horizon
        + matrix.exclusions.insufficient_data
        + matrix.exclusions.null_features
        == matrix.exclusions.candidate_rows
    )


def test_labelled_rows_have_availability_columns_and_no_fold_roles() -> None:
    close = (100.0, 101.0, 102.0, 103.0, 104.0)
    matrix = _build(
        close=close,
        feature_values=(1.0, 1.0, 1.0, 1.0, 1.0),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("2m")),
        horizon_bars=2,
    )

    assert {"detected_at", "available_at", "label_end_at"}.issubset(matrix.rows.columns)
    assert "fold_role" not in matrix.rows.columns
    assert "fold_id" not in matrix.rows.columns
    assert matrix.rows.get_column("detected_at").null_count() == 0
    assert matrix.rows.get_column("available_at").null_count() == 0
    assert matrix.rows.get_column("label_end_at").null_count() == 0


def test_log_of_non_positive_is_excluded_as_null_feature() -> None:
    close = (100.0, 101.0, 102.0, 103.0, 104.0)
    matrix = _build(
        close=close,
        feature_values=(math.e, 0.0, -1.0, math.e, math.e),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("1m")),
        horizon_bars=1,
        transform=FeatureTransform.LOG,
    )

    assert matrix.exclusions.null_features == 2
    assert matrix.rows.get_column("atr_14").to_list() == pytest.approx([1.0, 1.0])


def test_empty_frame_returns_empty_labelled_matrix() -> None:
    matrix = build_labelled_feature_matrix(
        frame=AnalysisFrame(timestamps=(), columns={"atr_14": ()}, column_lineage={}),
        ohlcv=_ohlcv_from_close(()),
        features=FeatureMatrixSpec(features=(_feature(),)),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("1m")),
        horizon_bars=1,
    )

    assert matrix.rows.height == 0
    assert matrix.exclusions.candidate_rows == 0
    assert matrix.exclusions.labelled_rows == 0
    assert {"detected_at", "available_at", "label_end_at", "label", "forward_return"}.issubset(
        matrix.rows.columns
    )


def test_horizon_bars_must_be_at_least_one() -> None:
    with pytest.raises(PredictiveMatrixError, match="horizon_bars must be at least 1"):
        _build(
            close=(100.0, 101.0),
            feature_values=(1.0, 1.0),
            label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("1m")),
            horizon_bars=0,
        )


def test_any_non_finite_feature_excludes_the_row() -> None:
    close = (100.0, 101.0, 102.0, 103.0, 104.0)
    timestamps = _timestamps(len(close))
    frame = AnalysisFrame(
        timestamps=timestamps,
        columns={
            "atr_14": (1.0, 2.0, math.nan, 4.0, 5.0),
            "ema_20": (1.0, 1.0, 1.0, 1.0, 1.0),
        },
        column_lineage={},
    )

    matrix = build_labelled_feature_matrix(
        frame=frame,
        ohlcv=_ohlcv_from_close(close),
        features=FeatureMatrixSpec(
            features=(_feature(alias="atr_14"), _feature(alias="ema_20")),
        ),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("1m")),
        horizon_bars=1,
    )

    assert matrix.exclusions.labelled_rows == 3
    assert matrix.exclusions.null_features == 1
    assert matrix.exclusions.incomplete_horizon == 1
    assert matrix.rows.get_column("atr_14").to_list() == [1.0, 2.0, 4.0]


def _atr_output_ref() -> OutputRef:
    dataset_ref = DatasetRef(
        DatasetId(
            instrument_id=Identifier("NQ.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id="sample",
        ),
        version=1,
    )
    identity = ComputationIdentity(
        component_id=ComponentId("volatility.atr"),
        component_version=ComponentVersion("1.0.0"),
        implementation_id=ImplementationId("numpy.atr"),
        implementation_version=ImplementationVersion("1.0.0"),
        parameters=CanonicalParameters.from_mapping({"period": 14}),
        dataset_ref=dataset_ref,
        computation_timeframe=Timeframe("1m"),
        requested_range=TimeRange(
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        ),
        dependency_keys=(),
    )
    return OutputRef(computation_identity=identity, output_id=OutputId("atr"))


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
