"""Sequence window spec, fold containment, gap drops, and accounting sidecar."""

from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

import trading_framework
from trading_framework.research.predictive import (
    WINDOW_ACCOUNTING_FILENAME,
    FoldRole,
    PaddingPolicy,
    PredictiveMatrixError,
    PredictiveSpecError,
    SequenceWindows,
    SequenceWindowSpec,
    WindowAccounting,
    build_sequence_windows,
    read_window_accounting,
    require_min_effective_sample,
    write_window_accounting,
)

_UTC = pl.Datetime(time_unit="us", time_zone="UTC")
_WINDOWS_SOURCE = (
    Path(trading_framework.__file__).resolve().parent / "research" / "predictive" / "windows.py"
)
_ML_LIBRARY_ROOTS = ("sklearn", "xgboost", "lightgbm", "catboost", "torch")
_START = datetime(2024, 1, 2, 14, 30, tzinfo=UTC)
_BAR = timedelta(minutes=1)


def _stamp(offset_minutes: int) -> datetime:
    return _START + timedelta(minutes=offset_minutes)


def _rows(
    *,
    roles: tuple[FoldRole, ...],
    entity_id: str = "NQ.c.0",
    fold_id: int = 0,
    gap_after: int | None = None,
    extra_entity: tuple[FoldRole, ...] | None = None,
) -> pl.DataFrame:
    records: list[dict[str, object]] = []
    minute = 0
    for index, role in enumerate(roles):
        records.append(
            {
                "entity_id": entity_id,
                "fold_id": fold_id,
                "available_at": _stamp(minute),
                "fold_role": role.value,
                "feat_a": float(index),
                "feat_b": float(index) * 10.0,
                "label": float(index) + 0.5,
            }
        )
        minute += 1
        if gap_after is not None and index == gap_after:
            minute += 5
    if extra_entity is not None:
        for index, role in enumerate(extra_entity):
            records.append(
                {
                    "entity_id": "ES.c.0",
                    "fold_id": fold_id,
                    "available_at": _stamp(index),
                    "fold_role": role.value,
                    "feat_a": 100.0 + index,
                    "feat_b": 200.0 + index,
                    "label": 0.25,
                }
            )
    return pl.DataFrame(
        records,
        schema={
            "entity_id": pl.String(),
            "fold_id": pl.Int64(),
            "available_at": _UTC,
            "fold_role": pl.String(),
            "feat_a": pl.Float64(),
            "feat_b": pl.Float64(),
            "label": pl.Float64(),
        },
    )


def _build(
    rows: pl.DataFrame,
    *,
    lookback: int = 4,
    stride: int = 1,
    fold_role: FoldRole = FoldRole.TEST,
    fold_id: int = 0,
) -> SequenceWindows:
    return build_sequence_windows(
        rows,
        spec=SequenceWindowSpec(lookback_bars=lookback, stride=stride),
        feature_columns=("feat_a", "feat_b"),
        bar_duration=_BAR,
        fold_role=fold_role,
        fold_id=fold_id,
    )


def test_spec_round_trip_and_identity_payload() -> None:
    spec = SequenceWindowSpec(lookback_bars=4, stride=2)
    restored = SequenceWindowSpec.from_dict(spec.to_dict())
    assert restored == spec
    assert spec.identity_payload() == {
        "lookback_bars": 4,
        "stride": 2,
        "padding_policy": PaddingPolicy.DROP.value,
    }


def test_spec_rejects_lookback_out_of_range() -> None:
    with pytest.raises(PredictiveSpecError, match="lookback_bars must be in"):
        SequenceWindowSpec(lookback_bars=1)
    with pytest.raises(PredictiveSpecError, match="lookback_bars must be in"):
        SequenceWindowSpec(lookback_bars=257)


def test_spec_rejects_non_drop_padding() -> None:
    with pytest.raises(PredictiveSpecError, match="padding_policy must be DROP"):
        SequenceWindowSpec.from_dict({"lookback_bars": 4, "padding_policy": "PAD"})


def test_spec_rejects_non_positive_stride() -> None:
    with pytest.raises(PredictiveSpecError, match="stride must be a positive integer"):
        SequenceWindowSpec(lookback_bars=4, stride=0)


def test_contiguous_test_windows_are_rank_three() -> None:
    roles = (FoldRole.TRAIN,) * 6 + (FoldRole.TEST,) * 8
    windows = _build(_rows(roles=roles), lookback=4, fold_role=FoldRole.TEST)

    assert windows.features.shape == (5, 4, 2)
    assert windows.target.shape == (5,)
    assert windows.accounting.windows_built == 5
    assert windows.accounting.windows_dropped_fold_boundary == 3
    assert windows.accounting.windows_dropped_incomplete == 0
    assert windows.accounting.effective_sample == 5
    np.testing.assert_allclose(windows.features[0, :, 0], [6.0, 7.0, 8.0, 9.0])
    assert all(entity == "NQ.c.0" for entity in windows.end_entity_ids)


def test_test_window_does_not_contain_non_test_roles() -> None:
    roles = (FoldRole.TRAIN,) * 4 + (FoldRole.PURGED,) * 2 + (FoldRole.TEST,) * 6
    windows = _build(_rows(roles=roles), lookback=4, fold_role=FoldRole.TEST)
    rows = _rows(roles=roles)
    test_stamps = set(windows.end_available_at)

    assert windows.accounting.windows_dropped_fold_boundary >= 1
    assert windows.features.shape[0] == 3
    for end_at in test_stamps:
        end_idx = rows.filter(
            (pl.col("available_at") == end_at) & (pl.col("fold_role") == FoldRole.TEST.value)
        )
        assert end_idx.height == 1


def test_train_windows_stay_inside_the_train_prefix() -> None:
    roles = (FoldRole.TRAIN,) * 8 + (FoldRole.PURGED,) * 2 + (FoldRole.TEST,) * 4
    windows = _build(_rows(roles=roles), lookback=4, fold_role=FoldRole.TRAIN)

    assert windows.accounting.windows_dropped_fold_boundary == 0
    assert windows.accounting.windows_built == 5
    assert windows.end_available_at[-1] == _stamp(7)


def test_gap_breaks_window_instead_of_bridging() -> None:
    roles = (FoldRole.TEST,) * 8
    windows = _build(_rows(roles=roles, gap_after=3), lookback=4, fold_role=FoldRole.TEST)

    assert windows.accounting.windows_dropped_gap == 3
    assert windows.accounting.windows_built == 2
    assert windows.accounting.windows_dropped_incomplete == 3
    assert windows.end_available_at == (_stamp(3), _stamp(12))


def test_incomplete_windows_are_dropped_never_padded() -> None:
    roles = (FoldRole.TEST,) * 3
    windows = _build(_rows(roles=roles), lookback=4, fold_role=FoldRole.TEST)

    assert windows.features.shape == (0, 4, 2)
    assert windows.accounting.windows_dropped_incomplete == 3
    assert windows.accounting.windows_built == 0


def test_entity_change_does_not_mix_windows() -> None:
    roles = (FoldRole.TEST,) * 5
    windows = _build(
        _rows(roles=roles, extra_entity=(FoldRole.TEST,) * 5),
        lookback=4,
        fold_role=FoldRole.TEST,
    )

    assert windows.features.shape[0] == 4
    assert set(windows.end_entity_ids) == {"NQ.c.0", "ES.c.0"}
    assert windows.end_entity_ids.count("NQ.c.0") == 2
    assert windows.end_entity_ids.count("ES.c.0") == 2


def test_stride_skips_candidate_end_rows() -> None:
    roles = (FoldRole.TEST,) * 8
    windows = _build(_rows(roles=roles), lookback=4, stride=2, fold_role=FoldRole.TEST)

    assert windows.accounting.candidate_end_rows == 4
    assert windows.accounting.windows_built == 2
    assert windows.features.shape[0] == 2


def test_fold_id_filter_ignores_other_folds() -> None:
    fold_0 = _rows(roles=(FoldRole.TEST,) * 6, fold_id=0)
    fold_1 = _rows(roles=(FoldRole.TEST,) * 6, fold_id=1).with_columns(
        pl.col("feat_a") + 50.0, pl.col("available_at") + timedelta(days=1)
    )
    windows = _build(pl.concat([fold_0, fold_1]), lookback=4, fold_role=FoldRole.TEST, fold_id=0)

    assert windows.accounting.fold_id == 0
    assert windows.features.shape[0] == 3
    assert float(windows.features[-1, -1, 0]) < 10.0


def test_embargoed_row_in_lookback_is_fold_boundary() -> None:
    roles = (FoldRole.EMBARGOED,) * 2 + (FoldRole.TEST,) * 5
    windows = _build(_rows(roles=roles), lookback=4, fold_role=FoldRole.TEST)

    assert windows.accounting.windows_dropped_fold_boundary >= 1
    assert windows.features.shape[0] == 2


def test_require_min_effective_sample_rejects_short_test() -> None:
    accounting = _build(
        _rows(roles=(FoldRole.TEST,) * 5),
        lookback=4,
        fold_role=FoldRole.TEST,
    ).accounting
    with pytest.raises(PredictiveSpecError, match="effective_sample"):
        require_min_effective_sample(accounting, minimum=10)


def test_window_accounting_sidecar_round_trip(tmp_path: Path) -> None:
    train = _build(
        _rows(roles=(FoldRole.TRAIN,) * 8 + (FoldRole.TEST,) * 4),
        lookback=4,
        fold_role=FoldRole.TRAIN,
    ).accounting
    test = _build(
        _rows(roles=(FoldRole.TRAIN,) * 8 + (FoldRole.TEST,) * 4),
        lookback=4,
        fold_role=FoldRole.TEST,
    ).accounting
    payload = WindowAccounting(entries=(train, test))
    path = tmp_path / WINDOW_ACCOUNTING_FILENAME
    write_window_accounting(path, payload)

    restored = read_window_accounting(path)
    assert restored.to_dict()["schema_version"] == "window_accounting.v1"
    assert restored.entries[0].effective_sample == train.effective_sample
    assert restored.entries[1].fold_role is FoldRole.TEST
    assert path.name == "window_accounting.json"


def test_missing_feature_column_raises() -> None:
    with pytest.raises(PredictiveMatrixError, match="missing required column: feat_b"):
        build_sequence_windows(
            _rows(roles=(FoldRole.TEST,) * 6).drop("feat_b"),
            spec=SequenceWindowSpec(lookback_bars=4),
            feature_columns=("feat_a", "feat_b"),
            bar_duration=_BAR,
            fold_role=FoldRole.TEST,
            fold_id=0,
        )


def test_purged_role_rejected_as_window_end() -> None:
    with pytest.raises(PredictiveSpecError, match="TRAIN or TEST"):
        _build(_rows(roles=(FoldRole.PURGED,) * 6), fold_role=FoldRole.PURGED)


def test_windows_module_does_not_import_ml_libraries() -> None:
    source = _WINDOWS_SOURCE.read_text(encoding="utf-8")
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
    assert "polars" in imported
    assert "numpy" in imported
