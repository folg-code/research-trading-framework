"""Tests for dashboard Plotly chart builders."""

from __future__ import annotations

import pyarrow as pa

from dashboard_app.charts import (
    build_monte_carlo_percentile_figure,
    build_monte_carlo_tail_figure,
    build_parameter_sweep_surface_figure,
    build_stress_delta_figure,
    build_walk_forward_fold_figure,
)
from dashboard_app.views.robustness import (
    ParameterSweepSliceKey,
    filter_parameter_sweep_slice,
    list_parameter_sweep_slices,
)


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


def test_list_and_filter_parameter_sweep_slices_separates_metric_axis_pairs() -> None:
    heatmap = pa.table(
        {
            "metric": ["net_pnl", "net_pnl", "net_pnl", "max_drawdown"],
            "x_axis": ["fast", "fast", "slow", "fast"],
            "y_axis": ["slow", "slow", None, None],
            "x_value": ["10", "20", "5", "10"],
            "y_value": ["5", "5", None, None],
            "value": [1.0, 2.0, 3.0, 4.0],
        }
    )

    slices = list_parameter_sweep_slices(heatmap)

    assert slices == (
        ParameterSweepSliceKey(metric="net_pnl", x_axis="fast", y_axis="slow"),
        ParameterSweepSliceKey(metric="max_drawdown", x_axis="fast", y_axis=None),
        ParameterSweepSliceKey(metric="net_pnl", x_axis="slow", y_axis=None),
    )
    filtered = filter_parameter_sweep_slice(heatmap, slices[0])
    assert filtered.num_rows == 2
    assert set(filtered.column("x_value").to_pylist()) == {"10", "20"}


def test_build_parameter_sweep_surface_figure_builds_surface_for_2d_slice() -> None:
    heatmap = pa.table(
        {
            "x_value": ["10", "20", "10", "20"],
            "y_value": ["1", "1", "2", "2"],
            "value": [1.0, 2.0, 3.0, 4.0],
        }
    )

    figure = build_parameter_sweep_surface_figure(
        heatmap,
        metric="net_pnl",
        x_axis="fast",
        y_axis="slow",
    )

    assert len(figure.data) == 1
    assert figure.data[0].type == "surface"
    assert [list(row) for row in figure.data[0].z] == [[1.0, 2.0], [3.0, 4.0]]
    assert "fast x slow" in str(figure.layout.title.text)


def test_build_parameter_sweep_heatmap_figure_builds_2d_grid() -> None:
    from dashboard_app.charts import build_parameter_sweep_heatmap_figure

    heatmap = pa.table(
        {
            "x_value": ["10", "20", "10", "20"],
            "y_value": ["1", "1", "2", "2"],
            "value": [1.0, 2.0, 3.0, 4.0],
        }
    )
    figure = build_parameter_sweep_heatmap_figure(
        heatmap,
        metric="net_pnl",
        x_axis="fast",
        y_axis="slow",
    )
    assert len(figure.data) == 1
    assert figure.data[0].type == "heatmap"
    heatmap = pa.table(
        {
            "x_value": ["20", "10"],
            "value": [2.5, 1.5],
        }
    )

    figure = build_parameter_sweep_surface_figure(
        heatmap,
        metric="net_pnl",
        x_axis="fast",
        y_axis=None,
    )

    assert len(figure.data) == 1
    assert figure.data[0].type == "scatter"
    assert list(figure.data[0].x) == ["10", "20"]
    assert list(figure.data[0].y) == [1.5, 2.5]


def test_build_stress_delta_figure_colors_negative_deltas() -> None:
    stress = pa.table(
        {
            "scenario_id": ["double_commission", "remove_top_trade"],
            "delta_net_pnl": ["-12.5", "3"],
        }
    )

    figure = build_stress_delta_figure(stress)

    assert list(figure.data[0].x) == [
        "Commission costs doubled",
        "Best single trade removed",
    ]
    assert list(figure.data[0].y) == [-12.5, 3.0]
    assert list(figure.data[0].marker.color) == ["#d62728", "#2ca02c"]


def test_build_monte_carlo_percentile_and_tail_figures() -> None:
    distributions = pa.table(
        {
            "method": ["trade_order_shuffle"],
            "p5_terminal_equity": [90.0],
            "p50_terminal_equity": [100.0],
            "p95_terminal_equity": [110.0],
        }
    )
    tails = pa.table(
        {
            "method": ["trade_order_shuffle"],
            "probability_terminal_pnl_negative": [0.2],
            "probability_max_drawdown_exceeds_threshold": [0.1],
        }
    )

    percentile = build_monte_carlo_percentile_figure(distributions)
    tail = build_monte_carlo_tail_figure(tails)

    assert len(percentile.data) == 3
    assert list(percentile.data[0].x) == ["Trade-order shuffle"]
    assert list(percentile.data[1].y) == [100.0]
    assert list(tail.data[0].y) == [0.2]
    assert list(tail.data[1].y) == [0.1]
