"""Tests for dashboard Plotly chart builders."""

from __future__ import annotations

import pyarrow as pa

from dashboard_app.charts import build_walk_forward_fold_figure


def test_build_walk_forward_fold_figure_groups_is_oos_by_fold_index() -> None:
    folds = pa.table(
        {
            "fold_index": [1, 0],
            "fold_id": ["fold-b", "fold-a"],
            "train_net_pnl": ["20.5", "10"],
            "oos_net_pnl": ["-1.25", "8.0"],
        }
    )

    figure = build_walk_forward_fold_figure(folds)

    assert len(figure.data) == 2
    assert figure.data[0].name == "Training (IS)"
    assert figure.data[1].name == "Unseen (OOS)"
    assert list(figure.data[0].x) == ["fold-a", "fold-b"]
    assert list(figure.data[0].y) == [10.0, 20.5]
    assert list(figure.data[1].y) == [8.0, -1.25]
    assert figure.layout.barmode == "group"


def test_build_walk_forward_fold_figure_empty_table() -> None:
    folds = pa.table(
        {
            "fold_index": pa.array([], type=pa.int64()),
            "train_net_pnl": pa.array([], type=pa.string()),
            "oos_net_pnl": pa.array([], type=pa.string()),
        }
    )

    figure = build_walk_forward_fold_figure(folds)

    assert figure.data == ()
    assert "Walk-forward" in str(figure.layout.title.text)


def test_build_walk_forward_fold_figure_falls_back_to_fold_number() -> None:
    folds = pa.table(
        {
            "fold_index": [0],
            "train_net_pnl": [3.5],
            "oos_net_pnl": [1.0],
        }
    )

    figure = build_walk_forward_fold_figure(folds)

    assert list(figure.data[0].x) == ["Fold 1"]
    assert list(figure.data[0].y) == [3.5]
    assert list(figure.data[1].y) == [1.0]
